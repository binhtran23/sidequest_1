# sale_granularity_v1 — falsified

Development ablation. **This variant does not improve on the champion and is retained
only as evidence.** Do not promote it.

## Hypothesis

Sale prices are dynamic with shared market inventory (`agents/COMPETITION_RULES.md`), so
a large SELL should flood the pool and clear at a depressed price. Observed on
2026-09-12, the rank-1 agent Majkel1337 never exceeded roughly 17 units in a step
(median 1–8), while our champion's SELL orders reach 1000 on seven of nine products.
Capping per-step sale size should therefore recover price.

The variant changes only the quantity on SELL orders the champion already decided to
place — never adding, removing or retiming a sale, never touching a purchase, hire or
unit action, and leaving the final-turn liquidation uncapped. `shed_pressure` lifts the
cap once the shed nears the 100-item overflow limit.

## Result

Six route-test-v1 screen seeds, both seats, opponent root `main.py`. The mirror control
(`main.py` against itself, same panel) returns 12 draws and a margin of exactly 0, so
these numbers carry no variance.

| Config | Wins | Mean margin | Dead plants | Escaped animals | Overflow |
| --- | ---: | ---: | ---: | ---: | ---: |
| cap=5 shed=40 | 0/12 | −15,133 | 30 | 0 | 813 |
| cap=10 shed=40 | 0/12 | −3,439 | 28 | 0 | 357 |
| cap=10 shed=60 | 0/12 | −3,921 | 28 | 0 | 442 |
| cap=20 shed=60 | 0/12 | −320 | 24 | 0 | 138 |
| cap=50 shed=80 | 0/12 | **+0** | 24 | 0 | 42 |
| cap=100 shed=80 | 0/12 | **+0** | 24 | 0 | 42 |
| `main.py` mirror | 12 draws | **0** | 24 | 0 | 42 |

Strictly monotone: every cap that binds costs coins, and none improves on the champion.
At cap=50 and above the cap never binds — margin is exactly 0 and the diagnostics match
the mirror control — which independently confirms that real per-step sale volume is far
below 50 units.

**Correction.** An earlier run of this sweep reported −18,399 / −7,336 / −7,805 / −3,951
/ −3,630. Those numbers carried a confound: this variant loaded `base/router.py`, which
runs `SALE_HORIZON = 2`, against a champion built with `SALE_HORIZON = 3`. That packaging
difference alone costs 3,630 coins per game on this panel, so every figure was overstated
by roughly that much and the "cap=50" row was entirely confound rather than cap. The
variant now sets `SALE_HORIZON` from settings, defaulting to the champion's 3, and the
table above is the corrected measurement. The conclusion is unchanged; the magnitudes
were not.

## Why the premise was wrong

The 1000-unit orders are a *sell-everything sentinel*, not a large sale. Measured over
six episodes per cohort, comparing each SELL order against the units that actually leave
the shed:

| | Mean units ordered | Mean units leaving shed | Fill ratio |
| --- | ---: | ---: | ---: |
| Majkel1337 | 3.9 | 3.60 | **0.92** |
| our champion | 243.4 | 2.50 | **0.01** |

Our orders fill at 1%. The engine clamps them to holdings, and the shed holds at most 100
non-seed items, so the champion was never flooding anything — it transacts 2.5 units per
sale against the leader's 3.6. The order sizes differ by two orders of magnitude; the
actual trade sizes do not.

Capping therefore did not reduce market impact, because there was none to reduce. It
converted "sell whatever I hold" into "sell at most N", throttling the sale pipeline.
At tight caps the stock backed up and the shed discarded it (859 overflow units at
cap=5). At cap=50 overflow returns to the champion's own 42 and the loss narrows to
−3,630 — still a loss, because the sales the cap blocks were worth making.

(Fill ratios are lower bounds: units harvested into the shed on the same step net against
the measured decrease. This does not affect the conclusion, which rests on the
denominator.)

## Reproduce

```bash
.venv/bin/python benchmark.py \
  --agent agents/slices/kaggriculture-most-powerful-route/variants/sale_granularity_v1/main.py \
  --opponent main.py --both-seats \
  --seeds 785985614 2080455400 458333647 1669076510 56669821 825367279
```

Receipts: `experiments/leader-route-20260912/sale-granularity-sweep/`.
Analysis: `experiments/leader-route-20260912/report.md`, section 5.
