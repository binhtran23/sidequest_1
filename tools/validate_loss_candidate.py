"""Verify optimized copies, frozen controls and isolated source loading."""
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'agents/slices/kaggriculture-most-powerful-route/variants/loss_upgrade_v1'
OUT = ROOT/'experiments/loss-upgrade-validation-20260912'


def load(path):
    spec = importlib.util.spec_from_file_location('loss_validation',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable
    count = 0
    for path in sorted((ROOT/'evidence/raw/champion-losses-20260912').glob('episode-*-replay.json')):
        replay = json.loads(path.read_text())
        seat = replay['info']['TeamNames'].index('Bình Trần Thanh')
        candidate, champion = load(FOLDER/'main.py'),load(ROOT/'main.py')
        candidate._LOSS_SETTINGS = {}
        before = json.dumps(candidate._INLINE_TAPES,separators=(',',':'))
        for step,states in enumerate(replay['steps'][:-1]):
            obs = copy.deepcopy(states[seat]['observation'])
            obs['step'],obs['player'] = step,seat
            assert candidate.agent(copy.deepcopy(obs)) == champion.agent(copy.deepcopy(obs)), (path.name,step)
            candidate.drain_telemetry()
            champion.drain_telemetry()
            count += 1
        assert before == json.dumps(candidate._INLINE_TAPES,separators=(',',':'))
    assert count == 10785, 'Local parity corpus missing or changed'
    start = time.perf_counter()
    assert get_last_callable((FOLDER/'main.py').read_text()).__name__ == 'agent'
    cold_ms = (time.perf_counter()-start)*1000
    with tempfile.TemporaryDirectory(prefix='loss-candidate-check-') as temporary:
        isolated = Path(temporary)/'main.py'
        shutil.copyfile(FOLDER/'main.py',isolated)
        previous = Path.cwd()
        try:
            os.chdir(temporary)
            env = make('kaggriculture',configuration={'seed':61007},debug=True)
            env.run([str(isolated),'starter'])
            assert len(env.steps) == 720
            assert [s.status for s in env.steps[-1]] == ['DONE','DONE']
            errors = [log for logs in env.logs for log in logs if log.get('stderr')]
            assert not errors,errors
            scores = [s.reward for s in env.steps[-1]]
        finally:
            os.chdir(previous)
    result = {'candidate_sha256':hashlib.sha256((FOLDER/'main.py').read_bytes()).hexdigest(),
              'disabled_action_parity':count,'action_mismatches':0,'tapes_unchanged':True,
              'isolated_loader':'passed','isolated_scores':scores,'cold_load_ms':cold_ms,
              'status_errors':0}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'parity-and-loader.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
