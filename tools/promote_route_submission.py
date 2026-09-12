"""Validate the gate, print a root promotion patch, then package the promoted file."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "agents/slices/kaggriculture-most-powerful-route/variants/submission_v1/main.py"
EVIDENCE = ROOT / "experiments/route-v1-package-20260912"
FINAL = ROOT / "experiments/route-v1-package-final-20260912"
VERSION = "route-v1-h3-20260912"


def gate():
    checksum = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
    parity = json.loads((EVIDENCE / "parity-and-loader.json").read_text())
    benchmark = json.loads((FINAL / "benchmark.summary.json").read_text())
    config = json.loads((FINAL / "config.resolved.json").read_text())
    assert parity["candidate_sha256"] == config["candidate_sha256"] == checksum
    assert parity["action_parity"] == 10785 and parity["action_mismatches"] == 0
    assert parity["read_only_tapes"] and parity["isolated_source_loader"] == "passed"
    assert benchmark["errors"] == benchmark["status_errors"] == 0
    assert benchmark["wins"] == benchmark["games"] and benchmark["mean_coin_margin"] > 0
    assert benchmark["mean_action_ms"] <= benchmark["opponent_mean_action_ms"]
    assert benchmark["max_action_ms"] < 1000 and parity["cold_load_ms"] < 1000
    connection = sqlite3.connect(f"file:{ROOT / '.local/mlflow/mlflow.db'}?mode=ro", uri=True)
    assert connection.execute("SELECT status FROM runs WHERE run_uuid=?", (benchmark["run_id"],)).fetchone() == ("FINISHED",)
    children = connection.execute("SELECT r.status FROM runs r JOIN tags t ON r.run_uuid=t.run_uuid WHERE t.key='mlflow.parentRunId' AND t.value=?", (benchmark["run_id"],)).fetchall()
    assert len(children) == benchmark["games"] and all(s == ("FINISHED",) for s in children)
    return {"version":VERSION, "sha256":checksum, "gate":"passed", "parity":parity,
            "benchmark":benchmark, "candidate":str(CANDIDATE.relative_to(ROOT)),
            "previous_root_sha256":"6bab2539cecae032868da8c4d51846a492a23ad2e978ad2532c1cf80c107cc30"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    receipt = gate()
    current = ROOT / "main.py"
    if not args.finalize:
        assert hashlib.sha256(current.read_bytes()).hexdigest() == receipt["previous_root_sha256"]
        print("*** Begin Patch\n*** Update File: " + str(current) + "\n@@")
        print("\n".join("-" + line for line in current.read_text().splitlines()))
        print("\n".join("+" + line for line in CANDIDATE.read_text().splitlines()))
        print("*** End Patch")
        return
    assert current.read_bytes() == CANDIDATE.read_bytes()
    folder = ROOT / "submission" / VERSION
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(current, folder / "main.py")
    (folder / "SHA256SUMS").write_text(receipt["sha256"] + "  main.py\n")
    (folder / "manifest.json").write_text(json.dumps(receipt, indent=2)+"\n")
    shutil.copyfile(FINAL / "benchmark.summary.json", folder / "benchmark-receipt.json")
    base = CANDIDATE.parents[2] / "base"
    for name in ("LICENSE.txt", "NOTICE.txt"):
        shutil.copyfile(base / name, folder / name)
    (EVIDENCE / "promotion.json").write_text(json.dumps({**receipt,"status":"promoted","submission_path":str(folder.relative_to(ROOT))}, indent=2)+"\n")
    assert (folder / "main.py").read_bytes() == current.read_bytes()
    print(json.dumps({"status":"promoted","file":str(folder / "main.py"),"sha256":receipt["sha256"]}))


if __name__ == "__main__":
    main()
