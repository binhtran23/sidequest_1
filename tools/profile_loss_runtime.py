"""Paired runtime diagnosis on identical, pre-holdout observation sequences."""
import hashlib
import importlib.util
import json
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT/'agents/slices/kaggriculture-most-powerful-route/variants/loss_upgrade_v1/main.py'


def load(path):
    spec=importlib.util.spec_from_file_location('runtime_diagnostic',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    files=sorted((ROOT/'evidence/raw/champion-losses-20260912').glob('episode-*.json'))[:3]
    if len(files)!=3:
        raise ValueError('Pre-holdout runtime corpus missing')
    samples=[]
    for path in files:
        replay=json.loads(path.read_text())
        seat=replay['info']['TeamNames'].index('Bình Trần Thanh')
        observations=[]
        for step,states in enumerate(replay['steps'][:-1]):
            obs=states[seat]['observation']
            obs['step'],obs['player']=step,seat
            observations.append(obs)
        modules={'candidate':load(CANDIDATE),'champion':load(ROOT/'main.py')}
        for repeat in range(11):
            measured={}
            order=('candidate','champion') if repeat%2==0 else ('champion','candidate')
            for name in order:
                module=modules[name]
                elapsed=0
                for obs in observations:
                    start=time.perf_counter_ns()
                    module.agent(obs,replay['configuration'])
                    elapsed+=time.perf_counter_ns()-start
                    module.drain_telemetry()
                measured[name]=elapsed/len(observations)/1000
            if repeat:  # discard one warm-up per workload and module
                samples.append({'episode_id':replay['info']['EpisodeId'],'repeat':repeat,
                                'candidate_us':measured['candidate'],'champion_us':measured['champion'],
                                'delta_us':measured['candidate']-measured['champion']})
    result={'candidate_sha256':hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
            'method':'30 alternating-order paired seasons on three pre-holdout replay sequences; time only agent calls; discard warm-up',
            'candidate_median_us':statistics.median(s['candidate_us'] for s in samples),
            'champion_median_us':statistics.median(s['champion_us'] for s in samples),
            'paired_median_delta_us':statistics.median(s['delta_us'] for s in samples),
            'slower_pairs':sum(s['delta_us']>0 for s in samples), 'pairs':len(samples),
            'samples':samples}
    out=ROOT/'experiments/loss-upgrade-validation-20260912/runtime-diagnostic.json'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))


if __name__=='__main__':
    main()
