#!/usr/bin/env python3
"""Collect and analyse leaderboard-scoring Kaggriculture top-team replays.

The command is intentionally manual and authenticated. It freezes a cohort
before downloading, writes immutable raw evidence, derives Parquet tables,
creates a static report, and logs one MLflow parent run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.top_replays import SCHEMA_VERSION
from tools.top_replays.api import KaggleReplayClient, capture_cohort, ensure_replay, sha256_file, utc_now
from tools.top_replays.mlflow_report import log_snapshot
from tools.top_replays.normalize import load_replay, normalize_snapshot, validate_referential_integrity
from tools.top_replays.report import write_report


SNAPSHOT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted"


def _tool_sha() -> str:
    digest = hashlib.sha256()
    paths = sorted((ROOT / "tools" / "top_replays").glob("*.py")) + [Path(__file__)]
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _snapshot_id() -> str:
    return "top-replays-" + utc_now().replace("-", "").replace(":", "").replace(".", "")


def _validate_manifest_configuration(manifest: dict, args: argparse.Namespace) -> None:
    cohort = manifest.get("cohort", {})
    actual = (cohort.get("competition"), cohort.get("top"), cohort.get("games_per_team"))
    requested = (args.competition, args.top, args.games_per_team)
    if actual != requested:
        raise ValueError(
            f"snapshot {manifest.get('snapshot_id')} is frozen with {actual}, not requested {requested}"
        )


def _validate_acceptance(manifest: dict) -> None:
    cohort = manifest["cohort"]
    per_team = {int(team["team_id"]): 0 for team in cohort["teams"]}
    for association in cohort["associations"]:
        per_team[int(association["team_id"])] += 1
    expected = int(cohort["games_per_team"])
    bad = {team: count for team, count in per_team.items() if count != expected}
    if bad:
        raise ValueError(f"team association counts do not equal {expected}: {bad}")
    episode_ids = {int(item["episode_id"]) for item in cohort["associations"]}
    raw_ids = [int(item["episode_id"]) for item in manifest.get("raw_files", [])]
    if len(raw_ids) != len(set(raw_ids)) or set(raw_ids) != episode_ids:
        raise ValueError("raw evidence is not a one-file-per-unique-episode set")


def _record_failure(manifest: dict, stage: str, message: str, episode_id: int | None = None) -> None:
    item = {"at": utc_now(), "stage": stage, "message": message}
    if episode_id is not None:
        item["episode_id"] = episode_id
    manifest.setdefault("failures", []).append(item)
    manifest["status"] = "failed"


def _provenance(record: dict, competition: str) -> dict:
    episode_id = int(record["episode_id"])
    path = Path(record["path"])
    record["path"] = path.relative_to(ROOT).as_posix() if path.is_absolute() else path.as_posix()
    record["provenance"] = {
        "provider": "Kaggle authenticated competition API",
        "competition": competition,
        "api_method": "competition_episode_replay",
        "uri": f"kaggle://competitions/{competition}/episodes/{episode_id}/replay",
    }
    return record


def _collect_raw(client, manifest: dict, manifest_path: Path, evidence_dir: Path) -> None:
    competition = manifest["cohort"]["competition"]
    episode_ids = sorted({int(item["episode_id"]) for item in manifest["cohort"]["associations"]})
    recorded = {int(item["episode_id"]): item for item in manifest.get("raw_files", [])}
    manifest["status"] = "downloading"
    _write_json(manifest_path, manifest)
    for episode_id in episode_ids:
        expected = recorded.get(episode_id)
        try:
            record, _downloaded = ensure_replay(client, evidence_dir, episode_id, expected)
            target = Path(record["path"])
            load_replay(target)
            record = _provenance(record, competition)
            recorded[episode_id] = record
            manifest["failures"] = [
                item for item in manifest.get("failures", []) if item.get("episode_id") != episode_id
            ]
            manifest["raw_files"] = [recorded[item] for item in sorted(recorded)]
            _write_json(manifest_path, manifest)
        except Exception as exc:
            _record_failure(manifest, "download_or_validation", str(exc), episode_id)
            _write_json(manifest_path, manifest)
    if manifest.get("failures"):
        raise RuntimeError(f"{len(manifest['failures'])} replay collection failures; see {manifest_path}")


def _new_manifest(snapshot_id: str, cohort: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "created_at": utc_now(),
        "status": "cohort_captured",
        "observer_only": True,
        "cohort": cohort,
        "raw_files": [],
        "failures": [],
        "tables": {},
        "reproducibility": {"git_sha": _git_sha(), "tool_sha256": _tool_sha()},
    }


def run(args: argparse.Namespace, client=None) -> dict:
    snapshot_id = args.snapshot_id or _snapshot_id()
    if not SNAPSHOT_PATTERN.fullmatch(snapshot_id):
        raise ValueError("snapshot id must contain only letters, digits, dot, underscore, or dash")
    experiment_dir = ROOT / "experiments" / snapshot_id
    raw_output = experiment_dir / "raw"
    evidence_dir = ROOT / "evidence" / "raw" / snapshot_id
    manifest_path = experiment_dir / "manifest.json"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        _validate_manifest_configuration(manifest, args)
    else:
        client = client or KaggleReplayClient()
        cohort = capture_cohort(client, args.competition, args.top, args.games_per_team)
        manifest = _new_manifest(snapshot_id, cohort)
        _write_json(manifest_path, manifest)  # Freeze before the first replay download.

    _write_json(experiment_dir / "config.json", {
        "competition": args.competition, "top": args.top,
        "games_per_team": args.games_per_team, "snapshot_id": snapshot_id,
        "observer_only": True,
    })

    # Stage failures are durable diagnostics, but a deliberate resume retries
    # normalization rather than making the snapshot permanently unrecoverable.
    manifest["failures"] = [
        item for item in manifest.get("failures", []) if item.get("stage") != "normalization"
    ]
    client = client or KaggleReplayClient()
    _collect_raw(client, manifest, manifest_path, evidence_dir)
    _validate_acceptance(manifest)
    if args.capture_only:
        manifest["status"] = "evidence_complete"
        _write_json(manifest_path, manifest)
        return manifest

    try:
        counts, tables = normalize_snapshot(manifest, ROOT, raw_output)
        validate_referential_integrity(tables, manifest)
        manifest["tables"] = {
            name: {
                "path": (raw_output / name).relative_to(ROOT).as_posix(),
                "rows": count,
                "sha256": sha256_file(raw_output / name),
                "byte_size": (raw_output / name).stat().st_size,
            }
            for name, count in counts.items()
        }
        manifest["status"] = "complete"
        manifest["completed_at"] = utc_now()
        _write_json(manifest_path, manifest)
        summary = write_report(experiment_dir / "report.html", manifest, tables)
        _write_json(experiment_dir / "summary.json", summary)
    except Exception as exc:
        _record_failure(manifest, "normalization", str(exc))
        _write_json(manifest_path, manifest)
        raise

    if not args.skip_mlflow:
        run_id = log_snapshot(ROOT, experiment_dir, manifest, summary)
        manifest["mlflow"] = {
            "tracking_uri": "sqlite:///" + str(ROOT / ".local" / "mlflow" / "mlflow.db"),
            "experiment": "kaggriculture.top_replays", "parent_run_id": run_id,
        }
        _write_json(manifest_path, manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default="kaggriculture")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--games-per-team", type=int, default=15)
    parser.add_argument("--snapshot-id", help="resume this frozen snapshot, or use this ID for a new one")
    parser.add_argument("--capture-only", action="store_true", help="stop after immutable evidence is complete")
    parser.add_argument("--skip-mlflow", action="store_true", help="build files without creating MLflow runs")
    args = parser.parse_args(argv)
    if args.top < 1 or args.games_per_team < 1:
        parser.error("--top and --games-per-team must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = run(args)
    except Exception as exc:
        print(f"collection failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "snapshot_id": manifest["snapshot_id"], "status": manifest["status"],
        "associations": len(manifest["cohort"]["associations"]),
        "unique_replays": len(manifest["raw_files"]), "tables": manifest.get("tables", {}),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
