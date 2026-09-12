"""Check the promotion gate against a benchmark receipt, then package the candidate.

Generalises `promote_route_submission.py`, which is pinned to the v1 promotion.
Run without `--finalize` to see the gate result and the diff that would land in
root `main.py`; run with it to copy the candidate over root and write
`submission/<version>/`.

The win condition is deliberately "beats the incumbent", not "wins every game".
The v1 gate required a clean sweep because it ran against a weaker base; a
candidate measured against the promoted champion itself is judged on margin and
points, and the losing seeds are recorded in the receipt rather than hidden.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STDLIB_ONLY = {"copy", "json", "zlib", "base64", "lzma", "math", "random", "sys",
               "collections", "itertools", "functools", "heapq", "os", "time", "re"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _self_contained(path: Path) -> list[str]:
    """A promoted file may not reach into this repository's packages."""
    tree = ast.parse(path.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return sorted(imported - STDLIB_ONLY)


def gate(candidate: Path, evidence: Path) -> dict:
    summary = json.loads((evidence / "benchmark.summary.json").read_text())
    config = json.loads((evidence / "config.resolved.json").read_text())
    checksum = _sha256(candidate)
    current = _sha256(ROOT / "main.py")

    foreign = _self_contained(candidate)
    assert not foreign, f"candidate imports non-stdlib modules: {foreign}"
    assert config["candidate_sha256"] == checksum, "receipt is for a different candidate"
    # The candidate has to have beaten the champion it is replacing, not an
    # older one, so both the recorded base and the opponent must be root today.
    assert config["base_sha256"] == current, "benchmark base is not the current root main.py"
    assert Path(config["opponent"]).resolve() == (ROOT / "main.py").resolve(), \
        "benchmark opponent was not root main.py"
    assert summary["errors"] == summary["status_errors"] == 0, "benchmark reported errors"
    assert summary["mean_coin_margin"] > 0 and summary["points_rate"] > 0.5, "no improvement"
    assert summary["mean_action_ms"] <= summary["opponent_mean_action_ms"], "runtime regression"
    assert summary["max_action_ms"] < 1000, "action latency over budget"

    connection = sqlite3.connect(f"file:{ROOT / '.local/mlflow/mlflow.db'}?mode=ro", uri=True)
    parent = connection.execute(
        "SELECT status FROM runs WHERE run_uuid=?", (summary["run_id"],)).fetchone()
    assert parent == ("FINISHED",), f"parent run is {parent}"
    children = connection.execute(
        "SELECT r.status FROM runs r JOIN tags t ON r.run_uuid=t.run_uuid "
        "WHERE t.key='mlflow.parentRunId' AND t.value=?", (summary["run_id"],)).fetchall()
    assert len(children) == summary["games"], f"{len(children)} child runs for {summary['games']} games"
    assert all(status == ("FINISHED",) for status in children), "incomplete child runs"
    return {"gate": "passed", "sha256": checksum, "previous_root_sha256": current,
            "candidate": str(candidate.relative_to(ROOT)),
            "evidence": str(evidence.relative_to(ROOT)),
            "benchmark": summary, "dependencies": config.get("dependency_sha256", {})}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--evidence", required=True, help="directory holding the benchmark receipt")
    parser.add_argument("--version", required=True)
    parser.add_argument("--license-dir",
                        default="agents/slices/kaggriculture-most-powerful-route/base")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args(argv)

    candidate = ROOT / args.candidate
    evidence = ROOT / args.evidence
    receipt = dict(gate(candidate, evidence), version=args.version)
    if not args.finalize:
        summary = receipt["benchmark"]
        print(json.dumps({k: receipt[k] for k in ("gate", "version", "sha256",
                                                  "previous_root_sha256")}, indent=2))
        print(f"would replace root main.py: {summary['wins']}-{summary['draws']}-"
              f"{summary['losses']} over {summary['games']} games, "
              f"{summary['mean_coin_margin']:+,.1f} coins/game")
        return 0

    shutil.copyfile(candidate, ROOT / "main.py")
    assert _sha256(ROOT / "main.py") == receipt["sha256"]
    folder = ROOT / "submission" / args.version
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(ROOT / "main.py", folder / "main.py")
    (folder / "SHA256SUMS").write_text(receipt["sha256"] + "  main.py\n")
    (folder / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    shutil.copyfile(evidence / "benchmark.summary.json", folder / "benchmark-receipt.json")
    shutil.copyfile(evidence / "config.resolved.json", folder / "benchmark-config.json")
    for name in ("LICENSE.txt", "NOTICE.txt"):
        shutil.copyfile(ROOT / args.license_dir / name, folder / name)
    (evidence / "promotion.json").write_text(json.dumps(
        {**receipt, "status": "promoted",
         "submission_path": str(folder.relative_to(ROOT))}, indent=2) + "\n")
    assert (folder / "main.py").read_bytes() == (ROOT / "main.py").read_bytes()
    print(json.dumps({"status": "promoted", "version": args.version,
                      "sha256": receipt["sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
