"""Print an apply_patch payload for a self-contained, unpromoted candidate.

The strategy layer is appended to a checksum-pinned base, so the candidate is
reproducible from its two inputs. The base is a parameter because the champion
moves: `loss_upgrade_v1` was composed onto route-v1-h3 and therefore never
carried V227, which route-v2-fert18 added. Pass `--base main.py` to compose the
same layer onto the current champion instead.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'agents/slices/kaggriculture-most-powerful-route/variants/loss_upgrade_v1'
CHAMPION_SHA = '09a1568d3aae9ecd4d0297aa4ffae6e65e2e4e4f0ab448faf63674574f881247'
DEFAULT_BASE = 'submission/route-v1-h3-20260912/main.py'


def source(base=DEFAULT_BASE, base_sha=CHAMPION_SHA, folder=FOLDER):
    frozen = ROOT / base
    if base_sha and hashlib.sha256(frozen.read_bytes()).hexdigest() != base_sha:
        raise ValueError(f'Base checksum mismatch for {base}')
    code = frozen.read_text() + '\n' + (folder/'strategy.py').read_text()
    # Audited tapes contain only primitive argument lists. Copy those lists
    # directly to preserve isolation without deepcopy's recursive dispatch.
    tapes_path = ROOT/'agents/slices/kaggriculture-most-powerful-route/base/actions.json'
    if hashlib.sha256(tapes_path.read_bytes()).hexdigest() != '17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef':
        raise ValueError('Audited tape checksum mismatch')
    tapes = json.loads(tapes_path.read_text())
    for tape in tapes:
        for action in tape:
            if set(action) != {'farmer','hands','market'}:
                raise ValueError('Unexpected tape action shape')
            for command in [action['farmer'],*action['hands'],*action['market']]:
                if not isinstance(command,list) or any(type(v) not in (str,int,float,bool,type(None)) for v in command):
                    raise ValueError('Non-primitive tape argument')
    old = '        action = copy.deepcopy(tape[step])'
    new = "        native = tape[step]\n        action = {'farmer': list(native['farmer']),\n                  'hands': [list(c) for c in native['hands']],\n                  'market': [list(o) for o in native['market']]}"
    if code.count(old) != 1:
        raise ValueError('Unexpected tape copy anchor')
    code = code.replace(old,new,1)
    old = "    market = action['market']\n    stock = projected_shed(action, view)\n    blocked ="
    new = "    market = action['market']\n    stock = getattr(view, '_sale_stock', None)\n    if stock is None:\n        stock = view._sale_stock = projected_shed(action, view)\n    blocked ="
    if code.count(old) != 1:
        raise ValueError('Unexpected sale projection anchor')
    code = code.replace(old,new,1)
    old = '        self.shed = {item: max(0, int(qty)) for item, qty in private["shed"].items()}'
    new = '        self.shed = dict(private["shed"])  # Engine contract: nonnegative integer quantities.'
    if code.count(old) != 1:
        raise ValueError('Unexpected inventory copy anchor')
    code = code.replace(old,new,1)
    old = "    changed=copy.deepcopy(action);changed['market']=orders"
    new = "    changed={'farmer':list(action['farmer']), 'hands':[list(c) for c in action['hands']], 'market':orders}"
    if code.count(old) != 1:
        raise ValueError('Unexpected market copy anchor')
    code = code.replace(old,new,1)
    ast.parse(code)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--write', action='store_true',
                        help='write the composed candidate instead of printing a patch')
    parser.add_argument('--base', default=DEFAULT_BASE)
    parser.add_argument('--base-sha', default=None,
                        help='expected base checksum; defaults to the pinned route-v1 hash')
    parser.add_argument('--variant', default=None,
                        help='variant folder name holding strategy.py; defaults to loss_upgrade_v1')
    args = parser.parse_args()
    folder = FOLDER if args.variant is None else FOLDER.parent / args.variant
    base_sha = args.base_sha
    if base_sha is None:
        base_sha = CHAMPION_SHA if args.base == DEFAULT_BASE else \
            hashlib.sha256((ROOT / args.base).read_bytes()).hexdigest()
    target = folder/'main.py'
    code = source(args.base, base_sha, folder)
    if args.check:
        if not target.exists() or target.read_text() != code:
            raise ValueError('Candidate does not match reproducible source')
        print(hashlib.sha256(code.encode()).hexdigest())
        return
    if args.write:
        target.write_text(code)
        print(json.dumps({'candidate': str(target.relative_to(ROOT)), 'base': args.base,
                          'base_sha256': base_sha,
                          'sha256': hashlib.sha256(code.encode()).hexdigest()}, indent=2))
        return
    print('*** Begin Patch')
    if target.exists():
        print('*** Update File: '+str(target)+'\n@@')
        print('\n'.join('-'+line for line in target.read_text().splitlines()))
    else:
        print('*** Add File: '+str(target))
    print('\n'.join('+'+line for line in code.splitlines()))
    print('*** End Patch')


if __name__ == '__main__':
    main()
