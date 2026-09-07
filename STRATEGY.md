# Astra — Kaggriculture one-shot entry

`main.py` is the complete submission: one `agent(observation, configuration)`
function, Python standard library only, no model weights or external services.
The original random entry is preserved in `baseline_random.py`.

Submitted once to Kaggle on 2026-09-06 as submission **56048186**.
Kaggle validation completed successfully (`SubmissionStatus.COMPLETE`); the
initial public score was **600.0**. This is an initial rating, not a settled
estimate of competitive strength.
The submitted `main.py` SHA-256 is
`6bab2539cecae032868da8c4d51846a492a23ad2e978ad2532c1cf80c107cc30`.

## Strategy

- Forecast market inventories from existing farms, scheduled crop and animal
  production, known shops, and a discounted estimate of future shop demand.
- Include feed costs, fertilizer consumption and yield bonuses, crop maturity,
  price crashes, and the remaining season when allocating capital.
- Reinvest in a mixture of crops and animals, with operating reserves for feed
  and workers. Expand up to three quadrants when the forecast justifies it.
- Each morning, build tile jobs and insert them into worker routes. Price the
  required workers using the actual Fibonacci hire costs. Prioritize crops
  ready for harvest and urgent watering or feeding.
- Assign selected harvest routes a trip to the shed when anticipated production
  would exceed storage. Sell deposited goods during that same turn.
- On the final day, route harvested goods back to storage before the last market
  action; unsold goods have no terminal value.

Plans are isolated by player and reset each day and each new episode. Purchases
are checked against the next observation before workers receive their routes.
The submission never imports the game engine or reads the opponent's private
inventory.

## Validation

Local environment: `kaggle-environments==1.32.7`, Python 3.11.15. The live replay
downloaded from the account's earlier submission matched the default rules.

| Opponent | Seeds / seats | Wins | Average final coins | Opponent average |
| --- | --- | ---: | ---: | ---: |
| Built-in starter | 0–7, player 0 | 8 / 8 | 184,990 | 3,531 |
| Earlier planner snapshot | 4–11, both seats | 14 / 16 | 96,533 | 87,265 |

The second opponent is `baseline_planner.py`, an earlier version developed in
this session, not an independent leaderboard opponent. The file named
`benchmark_holdout.json` represents eight distinct seeds, each played in both
positions. A later documentation audit found that seeds 4–7 had already appeared
in development runs; this is therefore a final evaluation set, not a completely
untouched holdout. The new subset, seeds 8–11, won 6/8 games across four distinct
seeds. Paired positions are correlated. These results are local benchmarks, not
a Kaggle rating or a claim of winning the competition.

All 24 games completed without agent errors, recorded nightly overflow, or
carried goods at the finish. The overflow counter instruments the nightly drop;
it does not separately measure discarded goods during midday DROP actions.
The largest measured decision took 76.2 ms on this machine, against
the default one-second action allowance. Full diagnostic reports are in
`benchmark_starter_final.json` and `benchmark_holdout.json`.

Additional smoke checks completed with a 120-turn season, 500 starting coins,
a 6×6 board, and a two-order market limit. These configurations are not tuned;
the restrictive market variant incurred crop and livestock losses. Ruff linting,
bytecode compilation, and a game loading the submission directly from its file
also passed.

This is a deterministic heuristic, not an optimal solver. Opponent expansion and
future shop draws remain uncertain, and overloaded farms can still lose plants
or animals. The local win rate should not be extrapolated to the leaderboard.

## Reproduce

```bash
.venv/bin/python benchmark.py --seeds 0 1 2 3 4 5 6 7 \
  --opponent starter --diagnostics --output benchmark_starter_final.json

.venv/bin/python benchmark.py --seeds 4 5 6 7 8 9 10 11 --both-seats \
  --opponent baseline_planner.py --diagnostics --output benchmark_holdout.json

ruff check main.py benchmark.py
```

Use `--replay replays/local.json` to save a benchmark replay. Development reports
with other names refer to earlier implementations or experimental parameters.
