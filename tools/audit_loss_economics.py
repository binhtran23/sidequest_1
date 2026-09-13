"""Re-adjudicate recorded actions with the local engine, not opponent code.

Validate every reconstructed cash balance against the next recorded state.
This establishes realized sale proceeds; it is not a counterfactual opponent.
"""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from kaggle_environments.envs.kaggriculture import kaggriculture as engine
from kaggle_environments.utils import structify
from tools.top_replays.api import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def audit(replay):
    rows = []
    cfg = replay['configuration']
    environment = SimpleNamespace(configuration=structify(cfg))
    original_commit = engine._commit_unit
    try:
        for step in range(len(replay['steps'])-1):
            before = replay['steps'][step]
            after = replay['steps'][step+1]
            farms = copy.deepcopy(before[0]['observation']['farms'])
            market = copy.deepcopy(before[0]['observation']['market'])
            market['params'] = engine._resolve_market_params(cfg.get('marketParams',{}))
            states = []
            for seat in (0,1):
                obs = SimpleNamespace(farms=farms,market=market,private=copy.deepcopy(before[seat]['observation']['private']))
                action = after[seat].get('action') or {}
                states.append(SimpleNamespace(observation=obs,action=action))
                commands = [action.get('farmer') or ['PASS'],*(action.get('hands') or [])]
                demand = Counter(c[1] for c in commands if len(c)>1 and c[0]=='PLANT')
                blocked = {c for c,n in demand.items() if n>obs.private['seeds'].get(c,0)}
                for unit,command in enumerate(commands):
                    if len(command)>1 and command[0]=='PLANT' and command[1] in blocked:
                        command = ['PASS']
                    engine._apply_unit_action(farms[seat],obs.private,unit,command,
                                             cfg['boardSize'],step//cfg['turnsPerDay'],cfg['turnsPerDay'],cfg['shedCapacity'])
            sales, quantities, purchases = [Counter(),Counter()],[Counter(),Counter()],[Counter(),Counter()]
            def commit(op,item,price,farm,private,market,shed_capacity=100):
                seat = 0 if farm is farms[0] else 1
                ok = original_commit(op,item,price,farm,private,market,shed_capacity)
                if ok:
                    if op=='SELL':
                        sales[seat][item] += price
                        quantities[seat][item] += 1
                    else:
                        purchases[seat][item] += price
                return ok
            engine._commit_unit = commit
            engine._process_market(states,environment)
            for seat in (0,1):
                actual = after[seat]['observation']['farms'][seat]['money']
                if farms[seat]['money'] != actual:
                    raise ValueError(f'Cash reconstruction mismatch at {step}, seat {seat}: {farms[seat]["money"]} != {actual}')
            rows.append({'step':step,'day':step//cfg['turnsPerDay'],
                         'sales':[dict(v) for v in sales], 'sale_quantities':[dict(v) for v in quantities],
                         'purchases':[dict(v) for v in purchases],
                         'money':[f['money'] for f in farms]})
    finally:
        engine._commit_unit = original_commit
    return {'episode_id':replay['info']['EpisodeId'],'teams':replay['info']['TeamNames'],
            'validated_transitions':len(rows),'turns':rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--episodes',type=int,nargs='+',required=True)
    args = parser.parse_args()
    folder = ROOT/'experiments'/args.snapshot
    manifest = json.loads((folder/'manifest.json').read_text())
    records = {r['episode_id']:r for r in manifest['raw_files']}
    results = []
    for episode in args.episodes:
        record = records[episode]
        path = ROOT/record['path']
        if sha256_file(path) != record['sha256']:
            raise ValueError('Evidence checksum changed')
        result = audit(json.loads(path.read_text()))
        results.append(result)
        print(episode,'validated',result['validated_transitions'],flush=True)
    (folder/'economic-audit.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__ == '__main__':
    main()
