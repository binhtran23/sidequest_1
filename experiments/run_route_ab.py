"""Run frozen route hypotheses through the required MLflow benchmark runner."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "experiments/route-test-v1-20260912"
SLICE = "agents/slices/kaggriculture-most-powerful-route"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["screen", "holdout"], default="screen")
    parser.add_argument("--variants", nargs="+")
    parser.add_argument("--revision", default="r1")
    args = parser.parse_args()
    config = json.loads((CAMPAIGN / "config.json").read_text())
    variants = args.variants or (config["variants"] if args.phase == "screen" else ["test_v1"])
    seeds = config[args.phase + "_seeds"]
    results = []
    for variant in variants:
        identifier = f"route-v1-{args.phase}-{variant}-{args.revision}"
        directory = ROOT / "experiments" / identifier
        dependencies = [str(p.relative_to(ROOT)) for p in (ROOT / SLICE / "base").iterdir() if p.is_file()]
        dependencies += [SLICE + "/variants/test_v1/policy.py", SLICE + f"/variants/{variant}/settings.json",
                         "agents/slices/astra-current/base/main.py", "benchmark.py", "experiments/run_mlflow_benchmark.py"]
        expected = {p:hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(dependencies)}
        receipt = directory / "benchmark.summary.json"
        if receipt.exists():
            previous = json.loads((directory / "config.resolved.json").read_text())
            if previous.get("dependency_sha256") != expected or previous["seeds"] != seeds:
                raise ValueError(f"{identifier} is frozen with different sources or seeds; use a new revision")
        else:
            cmd = [sys.executable, str(ROOT / "experiments/run_mlflow_benchmark.py"),
                   "--experiment-id", identifier, "--candidate", SLICE + f"/variants/{variant}/main.py",
                   "--base", config["champion"], "--opponent", config["champion"],
                   "--seeds", *map(str, seeds), "--both-seats", "--debug", "--dependencies", *dependencies]
            print("Starting " + identifier, flush=True)
            subprocess.run(cmd, cwd=ROOT, check=True)
        summary = json.loads(receipt.read_text())
        results.append({"variant":variant, "experiment":identifier, **summary})
        if summary["errors"] or summary.get("status_errors"):
            raise RuntimeError(f"{identifier}: errors; inspect raw games before continuing")
    output = CAMPAIGN / f"{args.phase}-{args.revision}.json"
    output.write_text(json.dumps(results, indent=2)+"\n")
    print(json.dumps([{k:r[k] for k in ("variant","wins","draws","losses","mean_coin_margin","run_id")} for r in results], indent=2))


if __name__ == "__main__":
    main()
