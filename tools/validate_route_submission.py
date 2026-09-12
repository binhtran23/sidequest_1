"""Check package parity, read-only tapes, isolated Kaggle loading and receipts."""
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = ROOT / "agents/slices/kaggriculture-most-powerful-route"
PACKAGE = BASE / "variants/submission_v1/main.py"
OUT = ROOT / "experiments/route-v1-package-20260912"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted((ROOT / "evidence/raw/champion-losses-20260912").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        seat = replay["info"]["TeamNames"].index("Bình Trần Thanh")
        packaged = load(PACKAGE, "packaged")
        development = load(BASE / "variants/test_v1/main.py", "development")
        before = json.dumps(packaged._INLINE_TAPES, separators=(",", ":"))
        for step, states in enumerate(replay["steps"][:-1]):
            obs = copy.deepcopy(states[seat]["observation"])
            obs["step"], obs["player"] = step, seat
            expected = development.agent(copy.deepcopy(obs), replay["configuration"])
            actual = packaged.agent(copy.deepcopy(obs), replay["configuration"])
            if expected != actual:
                raise AssertionError(f"Action mismatch: {path.name}, {step}")
            development.drain_telemetry()
            packaged.drain_telemetry()
            count += 1
        assert before == json.dumps(packaged._INLINE_TAPES, separators=(",", ":")), "Tapes mutated"
    assert count == 10785
    # Test the real file loader without __file__, development paths or assets.
    cold_start = time.perf_counter()
    entry = get_last_callable(PACKAGE.read_text())
    assert entry.__name__ == "agent", "Kaggle would select the wrong callable"
    cold_load_ms = (time.perf_counter()-cold_start)*1000
    with tempfile.TemporaryDirectory(prefix="route-submit-check-") as temporary:
        isolated = Path(temporary) / "main.py"
        shutil.copyfile(PACKAGE, isolated)
        previous = Path.cwd()
        try:
            os.chdir(temporary)
            env = make("kaggriculture", configuration={"seed": 61000}, debug=True)
            env.run([str(isolated), "starter"])
            assert len(env.steps) == 720
            assert [s.status for s in env.steps[-1]] == ["DONE", "DONE"]
            errors = [log for logs in env.logs for log in logs if log.get("stderr")]
            assert not errors, errors
            scores = [s.reward for s in env.steps[-1]]
        finally:
            os.chdir(previous)
    receipt = {"candidate_sha256": hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),
               "action_parity": count, "action_mismatches": 0, "read_only_tapes": True,
               "isolated_source_loader": "passed", "isolated_scores": scores,
               "cold_load_ms": cold_load_ms, "status_errors": 0}
    (OUT / "parity-and-loader.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
