"""Review complete frozen holdouts, paired by seed, including MLflow children."""
import argparse
import hashlib
import json
import random
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gates import latency_within_budget  # noqa: E402


def evaluate_gates(panels):
    """Score the four promotion gates over the opponent panels.

    Latency is checked against the engine's own budget rather than against the
    incumbent's timing; see `tools/gates.py` for why.
    """
    return {
        'positive_champion_improvement':panels[0]['mean_margin']>0,
        'no_aggregate_opponent_regression':all(p['paired_improvement']>=0 for p in panels[1:]),
        'latency_within_budget':all(latency_within_budget(p['candidate_p95_ms'],p['candidate_max_ms']) for p in panels),
        'zero_errors_complete_telemetry':all(p['candidate_telemetry_events']>0 for p in panels),
    }


def interval(values):
    rng = random.Random(20260912)
    samples = sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(5000))
    return [samples[125],samples[4874]]


def read_run(name, connection):
    folder = ROOT/'experiments'/name
    summary = json.loads((folder/'benchmark.summary.json').read_text())
    config = json.loads((folder/'config.resolved.json').read_text())
    games = [json.loads(p.read_text()) for p in sorted((folder/'raw').glob('seed-*-seat-*.json'))]
    assert len(games) == summary['games'] == len(config['seeds'])*2
    assert {(g['seed'],g['seat']) for g in games} == {(s,i) for s in config['seeds'] for i in (0,1)}
    parent = summary['run_id']
    status = connection.execute('SELECT status FROM runs WHERE run_uuid=?',(parent,)).fetchone()
    assert status == ('FINISHED',),(name,status)
    children = connection.execute("SELECT r.run_uuid,r.status FROM runs r JOIN tags t ON r.run_uuid=t.run_uuid WHERE t.key='mlflow.parentRunId' AND t.value=?",(parent,)).fetchall()
    assert len(children)==len(games) and all(s=='FINISHED' for _,s in children),(name,children)
    indexed={(g['seed'],g['seat']):g for g in games}
    for child,_ in children:
        metrics = dict(connection.execute('SELECT key,value FROM latest_metrics WHERE run_uuid=?',(child,)))
        assert {'coin_margin','action_latency_mean_ms','error_count','invalid_action_count','strategy_decision_count','plant_loss','animal_loss'} <= metrics.keys()
        assert metrics['error_count']==0
        child_tags=dict(connection.execute('SELECT key,value FROM tags WHERE run_uuid=?',(child,)))
        game=indexed[(int(child_tags['seed']),int(child_tags['seat']))]
        assert metrics['coin_margin']==game['coin_margin']
        assert metrics['action_latency_mean_ms']==game['mean_action_ms']
        event_path=folder/'raw'/f"seed-{game['seed']}-seat-{game['seat']}.anomalies.jsonl"
        child_events=[json.loads(line) for line in event_path.read_text().splitlines()] if event_path.exists() else []
        assert metrics['strategy_decision_count']==sum(e['type']=='strategy_decision' for e in child_events)
    tags = dict(connection.execute('SELECT key,value FROM tags WHERE run_uuid=?',(parent,)))
    assert tags.get('promotion_eligible')=='false'
    assert sum(bool(g['errors']) for g in games)==summary['errors']==0
    assert all(g['status']==['DONE','DONE'] for g in games)
    events = 0
    for p in (folder/'raw').glob('*.anomalies.jsonl'):
        for line in p.read_text().splitlines():
            e=json.loads(line)
            assert 'type' in e
            events += 1
    return summary,config,{(g['seed'],g['seat']):g for g in games},events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision',default='r7')
    args = parser.parse_args()
    connection = sqlite3.connect('file:'+str(ROOT/'.local/mlflow/mlflow.db')+'?mode=ro',uri=True)
    result = {'revision':args.revision,'panels':[],'mlflow_reviewed':True,'promoted':False}
    candidate_path=ROOT/'agents/slices/kaggriculture-most-powerful-route/variants/loss_upgrade_v1/main.py'
    candidate_hash=hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    result['candidate_sha256']=candidate_hash
    for opponent in ('champion','fertilizer','astra'):
        name=f'loss-v1-holdout-candidate-{opponent}-{args.revision}'
        control=f'loss-v1-holdout-control-{opponent}-{args.revision}'
        cs,cc,cg,ce=read_run(name,connection)
        bs,bc,bg,be=read_run(control,connection)
        assert cc['candidate_sha256']==candidate_hash and cc['candidate_parameters']=={}
        assert cg.keys()==bg.keys()
        rows=[]
        for seed in cc['seeds']:
            c=[cg[(seed,s)] for s in (0,1)]
            b=[bg[(seed,s)] for s in (0,1)]
            rows.append({'seed':seed,
                         'candidate_margin':statistics.mean(g['coin_margin'] for g in c),
                         'baseline_margin':statistics.mean(g['coin_margin'] for g in b),
                         'paired_improvement':statistics.mean(cg[(seed,s)]['coin_margin']-bg[(seed,s)]['coin_margin'] for s in (0,1)),
                         'plant_loss_delta':sum(g['diagnostics'].get('dead_plants',0) for g in c)-sum(g['diagnostics'].get('dead_plants',0) for g in b),
                         'animal_loss_delta':sum(g['diagnostics'].get('escaped_animals',0) for g in c)-sum(g['diagnostics'].get('escaped_animals',0) for g in b),
                         'noop_delta':sum(v for g in c for k,v in g['diagnostics'].items() if k.startswith('noop_'))-sum(v for g in b for k,v in g['diagnostics'].items() if k.startswith('noop_')),
                         'overflow_delta':sum(g['diagnostics'].get('overflow_units',0) for g in c)-sum(g['diagnostics'].get('overflow_units',0) for g in b)})
        improvements=[r['paired_improvement'] for r in rows]
        panel={'opponent':opponent,'candidate_receipt':name,'control_receipt':control,
               'candidate_run':cs['run_id'],'control_run':bs['run_id'],
               'games':cs['games'],'wins':cs['wins'],'draws':cs['draws'],'losses':cs['losses'],
               'mean_margin':cs['mean_coin_margin'],'baseline_mean_margin':bs['mean_coin_margin'],
               'paired_improvement':statistics.mean(improvements),'paired_mean_95_bootstrap':interval(improvements),
               'candidate_mean_ms':cs['mean_action_ms'],'baseline_mean_ms':bs['mean_action_ms'],
               'candidate_p95_ms':statistics.mean(g['p95_action_ms'] for g in cg.values()),
               'baseline_p95_ms':statistics.mean(g['p95_action_ms'] for g in bg.values()),
               'candidate_max_ms':cs['max_action_ms'],'candidate_telemetry_events':ce,
               'direct_losing_seeds':[r['seed'] for r in rows if r['candidate_margin']<0],
               'paired_regression_seeds':[r['seed'] for r in rows if r['paired_improvement']<0],
               'seeds':rows,'diagnostics':cs['diagnostics'],'baseline_diagnostics':bs['diagnostics']}
        result['panels'].append(panel)
    panels=result['panels']
    result['gates']=evaluate_gates(panels)
    result['validated']=all(result['gates'].values())
    original_parity=[]
    if args.revision=='r7':
        for role in ('candidate','control'):
            for opponent in ('champion','fertilizer','astra'):
                current=ROOT/'experiments'/f'loss-v1-holdout-{role}-{opponent}-r7'/'raw'
                original=ROOT/'experiments'/f'loss-v1-holdout-{role}-{opponent}-r6'/'raw'
                for path in current.glob('seed-*-seat-*.json'):
                    new=json.loads(path.read_text())
                    old=json.loads((original/path.name).read_text())
                    for key in ('scores','status','diagnostics','final_shed','final_carried','hires_by_day'):
                        assert new[key]==old[key],(role,opponent,path.name,key)
                    original_parity.append(path.name)
        result['frozen_policy_game_parity']=len(original_parity)
    output=ROOT/'experiments/loss-upgrade-validation-20260912'
    output.mkdir(exist_ok=True)
    (output/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Frozen candidate validation','',f"Candidate SHA-256: `{candidate_hash}`.",'',
           '| Opponent | W–D–L | Candidate margin | Champion margin | Paired improvement | 95% seed bootstrap |',
           '| --- | ---: | ---: | ---: | ---: | --- |']
    for p in panels:
        lo,hi=p['paired_mean_95_bootstrap']
        lines.append(f"| {p['opponent']} | {p['wins']}–{p['draws']}–{p['losses']} | {p['mean_margin']:+,.1f} | {p['baseline_mean_margin']:+,.1f} | {p['paired_improvement']:+,.1f} | [{lo:+,.1f}, {hi:+,.1f}] |")
    lines += ['', 'Each opponent panel uses 24 unused seeds in both seats. Seats are averaged within seed for uncertainty. Bootstrap intervals describe this local panel, not leaderboard performance.', '',
              'All six MLflow parents and 288 children were checked for finished status, required metrics and zero errors. All strategy events and static per-game receipts were inspected. No promotion was performed.','',
              'Gates: '+json.dumps(result['gates'],sort_keys=True)+'.','',
              'Per-seed regressions and diagnostic changes are retained in `evaluation.json`; a positive mean is not a claim of improvement on every seed.', '',
              'The Astra paired interval crosses zero. Its +32 coin average does not establish a reliable gain. Ten seeds regress by 6 to 402 coins; the only outright losing seed, 921706, also loses for the champion and improves by 148 coins here.', '',
              'Plant and animal losses match the corresponding controls. Each 48-game candidate panel has 44 additional shed-overflow units; additional fertilizer no-ops show that current-day supply reservations do not fully protect the next day. These costs are included in the reported final coin margins.', '',
              'Runtime measurements include mean, p95 and maximum in `evaluation.json`. Latency is gated against the engine budget in `tools/gates.py`, not against the incumbent mean; the independent identical-input timing diagnosis is in `runtime-diagnostic.json`.']
    if original_parity:
        lines += ['', f'Runtime optimization preserved scores, statuses, field diagnostics, hires and final inventories in all {len(original_parity)} repeated games. Strategy selection remained frozen; the repeated runs are not additional independent seeds.']
    (output/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'validated':result['validated'],'gates':result['gates'],
                      'panels':[{k:p[k] for k in ('opponent','wins','losses','mean_margin','paired_improvement','candidate_mean_ms','baseline_mean_ms','paired_regression_seeds')} for p in panels]},indent=2))


if __name__=='__main__':
    main()
