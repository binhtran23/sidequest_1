"""Reproducible loss-driven screens and frozen, unused-seed validation."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLICE = 'agents/slices/kaggriculture-most-powerful-route/variants'
CANDIDATE = SLICE+'/loss_upgrade_v1/main.py'
FERTILIZER = SLICE+'/fertilizer_use_v1/main.py'
CHAMPION = 'submission/route-v1-h3-20260912/main.py'
ASTRA = 'agents/slices/astra-current/base/main.py'
SCREEN = [785985614,2080455400,458333647,1669076510,56669821,825367279]
HOLDOUT = list(range(921700,921724))
ARMS = {
    'control': {'fertilizer':'none','sale_horizon':3,'late_harvest':False},
    'window': {'fertilizer':'window','sale_horizon':3,'late_harvest':False},
    'sale4': {'fertilizer':'none','sale_horizon':4,'late_harvest':False},
    'late': {'fertilizer':'none','sale_horizon':3,'late_harvest':True},
    'combined': {'fertilizer':'legacy','sale_horizon':4,'late_harvest':False},
}


def run(identifier, candidate, opponent, seeds, parameters):
    dependencies = [CHAMPION, 'main.py', ASTRA, FERTILIZER, SLICE+'/fertilizer_use_v1/settings.json',
                    SLICE+'/loss_upgrade_v1/strategy.py', 'benchmark.py',
                    'experiments/run_mlflow_benchmark.py','experiments/run_loss_upgrade.py']
    fingerprints = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(dependencies)}
    folder = ROOT/'experiments'/identifier
    receipt = folder/'benchmark.summary.json'
    if receipt.exists():
        old = json.loads((folder/'config.resolved.json').read_text())
        expected = hashlib.sha256((ROOT/candidate).read_bytes()).hexdigest()
        if (old['candidate_sha256'] != expected or old['seeds'] != seeds
                or old['candidate_parameters'] != parameters or old['dependency_sha256'] != fingerprints
                or old['opponent'] != str(ROOT/opponent)):
            raise ValueError('Frozen experiment differs; choose a new revision: '+identifier)
    else:
        command = [sys.executable,'experiments/run_mlflow_benchmark.py','--experiment-id',identifier,
                   '--candidate',candidate,'--base',CHAMPION,'--opponent',opponent,
                   '--seeds',*map(str,seeds),'--both-seats','--debug','--parameters',json.dumps(parameters),
                   '--dependencies',*dependencies]
        print('Starting '+identifier, flush=True)
        subprocess.run(command,cwd=ROOT,check=True)
    summary = json.loads(receipt.read_text())
    if summary['errors'] or summary['status_errors']:
        raise RuntimeError('Benchmark failed; inspect '+identifier)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=['screen','holdout'],default='screen')
    parser.add_argument('--arms',nargs='+',default=['control','window','sale4','late'])
    parser.add_argument('--revision',default='r1')
    args = parser.parse_args()
    if args.phase == 'screen':
        for arm in args.arms:
            run(f'loss-v1-screen-{arm}-{args.revision}',CANDIDATE,CHAMPION,SCREEN,{'_LOSS_SETTINGS':ARMS[arm]})
    else:
        for name,opponent in [('champion',CHAMPION),('fertilizer',FERTILIZER),('astra',ASTRA)]:
            run(f'loss-v1-holdout-candidate-{name}-{args.revision}',CANDIDATE,opponent,HOLDOUT,{})
            run(f'loss-v1-holdout-control-{name}-{args.revision}',CHAMPION,opponent,HOLDOUT,{})


if __name__ == '__main__':
    main()
