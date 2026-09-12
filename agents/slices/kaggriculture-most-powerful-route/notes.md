# Kaggriculture Most Powerful Route

This slice is a static, byte-exact extraction of
`kaggriculture-most-powerfull-route.ipynb`. The notebook was parsed as JSON and
its embedded Base64/gzip assets were decoded as data. No notebook cell or
extracted Python module was executed during extraction.

## Project layout

| File | Purpose | Notebook origin |
| --- | --- | --- |
| `base/main.py` | Kaggle `agent(observation, configuration)` entrypoint | Cell 4 |
| `base/policy.py` | Validates settings, loads `router.py`, and creates isolated policy state | Cell 5 |
| `base/router.py` | Route selection, action repairs, opportunistic strategies, and sale-window logic | Cell 6 |
| `base/settings.json` | Selects the two-turn sale horizon | Cell 3 |
| `base/actions.json` | All 13 precomputed 719-turn action tapes | Embedded asset in cell 7 |
| `base/LICENSE.txt` | Apache 2.0 license | Embedded asset in cell 7 |
| `base/NOTICE.txt` | Attribution and modification history | Embedded asset in cell 7 |

The notebook's other cells are build orchestration rather than agent modules:

| Cell | Role in the notebook |
| --- | --- |
| 0 | Human-readable build description |
| 1 | Pins `kaggle-environments==1.32.7` |
| 2 | Selects `/kaggle/working` (or the current directory) as the build directory |
| 3 | Writes `settings.json` |
| 4 | Writes `main.py` |
| 5 | Writes `policy.py` |
| 6 | Writes `router.py` |
| 7 | Restores and verifies `actions.json`, `LICENSE.txt`, and `NOTICE.txt` |
| 8 | Imports the generated entrypoint as a notebook smoke check |
| 9 | Creates and verifies deterministic `submission.tar.gz` and `build-receipt.json` |

## Runtime call path

1. `main.py` reads `settings.json` and dynamically loads `policy.py`.
2. `policy.py` checks that `sale_horizon` is 1, 2, or 3, then loads
   `router.py` and sets its `SALE_HORIZON` value.
3. `router.py` reads `actions.json`, verifies that it contains 13 tapes of 719
   actions, and exposes the final `agent` function.
4. On every callback, the route engine copies the action for the current step
   from the selected tape and applies its bounded reactive layers.

## Route selection

The agent starts on plan 0. At step 144 it examines the first two unlocked
shops and applies the following lookup; any unlisted pair stays on plan 0.
At step 648 it always switches to final plan 2.

| First shop | Second shop | Plan |
| --- | --- | ---: |
| BAKERY | YARN_STORE | 3 |
| BRUNCH_SPOT | YARN_STORE | 4 |
| FARMERS_MARKET | YARN_STORE | 5 |
| ICE_CREAM_SHOP | YARN_STORE | 6 |
| PET_CAFE | YARN_STORE | 5 |
| PIZZA_SHOP | YARN_STORE | 7 |
| SMOOTHIE_SHOP | YARN_STORE | 8 |
| YARN_STORE | BAKERY | 9 |
| YARN_STORE | BRUNCH_SPOT | 9 |
| YARN_STORE | FARMERS_MARKET | 1 |
| YARN_STORE | ICE_CREAM_SHOP | 9 |
| YARN_STORE | PET_CAFE | 10 |
| YARN_STORE | PIZZA_SHOP | 6 |
| YARN_STORE | SMOOTHIE_SHOP | 11 |
| YARN_STORE | YARN_STORE | 12 |

## Reactive layers in `router.py`

- Core router: replays a selected tape, inserts `DIG` before weed-blocked
  planting/building, projects shed contents, advances eligible sales, and
  liquidates products on the last callback.
- V216: may sell one wheat at step 23 to preserve enough cash for the planned
  first-day hires, while retaining at least two projected wheat.
- V217: uses otherwise idle farmer turns for a bounded starvation rescue when
  an animal has already missed feed.
- V218: during steps 712-718, assigns up to three otherwise idle workers to
  short fertilizer collection/return trips when the shed-capacity bound is safe.
- V219: conditionally opens the southeast land for a ten-tomato late-game
  investment, with dedicated observed workers, only when strict money, price,
  shop, land, and route checks pass.
- V224: moves already requested sales earlier in the market order list without
  crossing a same-item purchase.
- V226: buys a bounded wheat shortage when the next known action requires a
  wheat pickup and budget/capacity guards pass.
- Final sale-window layer: from step 288, moves eligible sales forward by up to
  two known actions, records debts against their original steps, and subtracts
  those quantities later to prevent duplicate sales.

## What is and is not present

This is a scripted/search-derived route portfolio with observation-based
repairs. It contains no model training, learned weights, replay result,
benchmark score, or leaderboard score. The original notebook's recorded output
only proves that the deterministic archive was built successfully; it records
`competition_submission_made: false` because uploading is a separate action.

## Integrity

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `LICENSE.txt` | 11,358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| `NOTICE.txt` | 1,058 | `266ef3ce6949038d19f778cf13f952a1f8fba4e1f3188b1c2b42e5a1e2933d3a` |
| `actions.json` | 5,099,830 | `17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef` |
| `main.py` | 1,083 | `495bfa4825c9e58638e804aeeb62a9537826f6d4d869222815e1bbeefd84d3dc` |
| `policy.py` | 835 | `5bc8d5635d90462e813569123de17b012762c30f3817b20457365a1155d6b908` |
| `router.py` | 44,013 | `3a444a70ea9dd89f3cb857676fcc0180ebf1dfb7ede89f7f0cc82a2ef384e380` |
| `settings.json` | 24 | `f6f4c047e25392849b258eeb940696ae8952ce155df68e2bd8ecc44163d6c46b` |

The notebook records the deterministic archive SHA-256 as
`d02b8e23992611fa928eba96ee0952948f672e737e5fd611712688614a077c4a`.

## Test version (2026-09-12)

`variants/test_v1/` is an experimental strategy wrapper around independently
loaded, unchanged champion source. Each sibling variant changes one setting
group; `control` changes none. These are strategy experiments, not extensions of
the restricted shared adaptive layer. Forecast and greedy insertion helpers come
from the statically audited `astra-current/base/main.py` source.

The five hypotheses are earlier sales, late carrot/wheat choice on the same
worker path, next-pickup feed supply, tomato investment profit, and final-day
harvest/delivery routes. Neither the full Astra policy nor an arbitrary
incompatible action tape is substituted mid-game.

The campaign configuration is `experiments/route-test-v1-20260912/config.json`.
Run it with `.venv/bin/python experiments/run_route_ab.py`; every individual
match goes through `experiments/run_mlflow_benchmark.py`. Dependencies, source
snapshots, per-game results, runtime, diagnostics and strategy decision events
are retained with explicit local MLflow tracking. The final report records which
switches were retained in `test_v1`; unsuccessful variants remain available.

These entrypoints depend on development files and are not submission packages.
No promotion or Kaggle upload is performed by the campaign.

## Subsequent promotion and submission

On the user's request, the selected policy was packaged as the self-contained
`variants/submission_v1/main.py`, validated through the actual Kaggle source
loader, and promoted after parity, runtime and benchmark gates passed.
Root `main.py` and `submission/route-v1-h3-20260912/main.py` are byte-identical.
Kaggle CLI upload succeeded with submission ID `56182079` (initially PENDING).
See `experiments/route-v1-package-20260912/report.md` for the gate and receipts.
