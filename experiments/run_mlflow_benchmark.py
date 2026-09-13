"""Run reproducible local benchmarks with explicit MLflow SQLite/artifact stores."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark import run_game
DB = ROOT / ".local" / "mlflow" / "mlflow.db"
ARTIFACTS = ROOT / ".local" / "mlflow" / "artifacts"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        return "uncommitted"


def _tracking_uri():
    return "sqlite:///" + str(DB)


def _artifact_uri():
    return ARTIFACTS.resolve().as_uri()


def _experiment(mlflow, name):
    existing = mlflow.get_experiment_by_name(name)
    return existing.experiment_id if existing else mlflow.create_experiment(name, artifact_location=_artifact_uri())


def _metric(game, key, default=0):
    value = game.get(key, default)
    return float(default if value is None else value)


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--candidate", default="agents/slices/astra-current/variants/adaptive_v1/main.py")
    parser.add_argument("--base", default="agents/slices/astra-current/base/main.py")
    parser.add_argument("--opponent", default="starter")
    parser.add_argument("--seeds", type=int, nargs="+", default=[20000, 20001, 20002, 20003])
    parser.add_argument("--both-seats", action="store_true")
    parser.add_argument("--config", default="{}")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--parameters", default="{}", help="Candidate module overrides; recorded in the receipt")
    parser.add_argument("--dependencies", nargs="*", default=[], help="Additional source/config files to fingerprint")
    args = parser.parse_args()

    import mlflow

    DB.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(_tracking_uri())
    experiment_id = _experiment(mlflow, "kaggriculture.benchmark")
    output = ROOT / "experiments" / args.experiment_id
    output.mkdir(parents=True, exist_ok=True)
    raw = output / "raw"
    raw.mkdir(exist_ok=True)
    candidate, base = ROOT / args.candidate, ROOT / args.base
    opponent = str((ROOT / args.opponent) if args.opponent.endswith(".py") else args.opponent)
    config = json.loads(args.config)
    parameters = json.loads(args.parameters)
    if not isinstance(parameters, dict):
        parser.error("--parameters must be a JSON object")
    resolved = {
        "candidate": str(candidate), "candidate_sha256": _sha256(candidate),
        "base": str(base), "base_sha256": _sha256(base), "opponent": opponent,
        "seeds": args.seeds, "seat_policy": "both" if args.both_seats else "seat_0",
        "configuration": config, "git_sha": _git_sha(),
        "candidate_parameters": parameters,
        "python": platform.python_version(), "mlflow": importlib.metadata.version("mlflow"),
        "kaggle_environments": importlib.metadata.version("kaggle-environments"),
        "dependency_sha256": {p: _sha256(ROOT / p) for p in sorted(args.dependencies)},
    }
    _write_json(output / "config.resolved.json", resolved)
    games = []
    with mlflow.start_run(experiment_id=experiment_id, run_name=args.experiment_id) as parent:
        sources = raw / "sources"
        for source in [args.candidate, args.base, *args.dependencies]:
            relative = (ROOT / source).resolve().relative_to(ROOT)
            target = sources / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        mlflow.log_artifacts(str(sources), "sources")
        mlflow.log_params({
            "candidate_sha256": resolved["candidate_sha256"], "base_sha256": resolved["base_sha256"],
            "git_sha": resolved["git_sha"], "opponent": opponent, "seed_panel": ",".join(map(str, args.seeds)),
            "seat_policy": resolved["seat_policy"], "configuration": json.dumps(config, sort_keys=True),
            "candidate_parameters": json.dumps(parameters, sort_keys=True),
        })
        for seed in args.seeds:
            for seat in (0, 1) if args.both_seats else (0,):
                with mlflow.start_run(run_name=f"seed-{seed}-seat-{seat}", nested=True):
                    game = run_game(str(candidate), opponent, seed, seat, config, diagnostics=True, parameters=parameters)
                    games.append(game)
                    events = game.pop("telemetry_events", [])
                    metrics = {
                        "points": _metric(game, "points"), "coin_margin": _metric(game, "coin_margin"),
                        "candidate_coins": _metric(game, "our_score"), "opponent_coins": _metric(game, "opponent_score"),
                        "action_latency_mean_ms": _metric(game, "mean_action_ms"), "action_latency_p95_ms": _metric(game, "p95_action_ms"),
                        "action_latency_max_ms": _metric(game, "max_action_ms"), "error_count": len(game["errors"]),
                        "invalid_action_count": sum(v for k, v in game["diagnostics"].items() if k.startswith("noop_")),
                        "override_count": sum(e["type"] == "override" for e in events),
                        "strategy_decision_count": sum(e["type"] == "strategy_decision" for e in events),
                        "maintenance_rescued": sum(e.get("guard_reason", "").startswith("urgent_") for e in events),
                        "plant_loss": game["diagnostics"].get("dead_plants", 0),
                        "animal_loss": game["diagnostics"].get("escaped_animals", 0),
                        "shed_overflow": game["diagnostics"].get("overflow_units", 0),
                        "terminal_inventory": sum(game["final_shed"].values()) + game["final_carried"],
                    }
                    mlflow.log_metrics(metrics)
                    if events:
                        anomaly = raw / f"seed-{seed}-seat-{seat}.anomalies.jsonl"
                        anomaly.write_text("".join(json.dumps(e) + "\n" for e in events))
                        mlflow.log_artifact(str(anomaly), "anomalies")
                    if args.debug or game["errors"]:
                        _write_json(raw / f"seed-{seed}-seat-{seat}.json", game)
                    mlflow.set_tags({"seed": seed, "seat": seat, "source_hash": resolved["candidate_sha256"]})
        summary = {
            "games": len(games), "points_rate": statistics.mean(g["points"] for g in games),
            "mean_coin_margin": statistics.mean(g["coin_margin"] for g in games),
            "errors": sum(bool(g["errors"]) for g in games),
            "max_action_ms": max(g["max_action_ms"] for g in games),
            "wins": sum(g["win"] for g in games),
            "draws": sum(g["draw"] for g in games),
            "losses": sum(not g["win"] and not g["draw"] for g in games),
            "status_errors": sum(any(s != "DONE" for s in g["status"]) for g in games),
            "mean_action_ms": statistics.mean(g["mean_action_ms"] for g in games),
            "opponent_mean_action_ms": statistics.mean(g["opponent_mean_action_ms"] for g in games),
            "opponent_max_action_ms": max(g["opponent_max_action_ms"] for g in games),
            "diagnostics": {key: sum(g["diagnostics"].get(key, 0) for g in games)
                            for key in sorted({key for g in games for key in g["diagnostics"]})},
            "terminal_inventory": sum(sum(g["final_shed"].values()) + g["final_carried"] for g in games),
            "run_id": parent.info.run_id,
        }
        _write_json(output / "benchmark.summary.json", summary)
        (output / "report.md").write_text("# Benchmark receipt\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in summary.items()) + "\n")
        mlflow.log_artifact(str(output / "config.resolved.json"))
        mlflow.log_artifact(str(output / "benchmark.summary.json"))
        mlflow.log_artifact(str(output / "report.md"))
        mlflow.log_metrics({"points_rate": summary["points_rate"], "mean_coin_margin": summary["mean_coin_margin"], "error_games": summary["errors"]})
        mlflow.set_tag("promotion_eligible", "false")
        print(json.dumps({"run_id": parent.info.run_id, **summary}, indent=2))


if __name__ == "__main__":
    main()
