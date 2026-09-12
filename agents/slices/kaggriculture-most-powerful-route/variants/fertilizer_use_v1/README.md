# fertilizer_use_v1

Apply fertilizer the champion already holds, on turns it had already decided to
idle, from day 18. **Confirmed: 46-0-2 over 48 holdout games, +203.8 coins/game.**

## Why

`experiments/season-curves-20260912/` measured per-day farm economics for the
frozen top-5 cohort and for 12 local games of root `main.py`. Fertilizer is the
one production input where the champion is last in the field:

| | fertilizer acquired | FERTILIZE actions | applied |
| --- | ---: | ---: | ---: |
| **champion** | **343.8** | **67.7** | **20%** |
| ymg_aq | 329.0 | 199.0 | 60% |
| Otter Vibe | 332.2 | 192.8 | 58% |
| Unknown Mother-Goose | 303.2 | 172.7 | 57% |
| Majkel1337 (rank 1) | 287.2 | 158.5 | 55% |
| Artem The Farmer 🍅 | 300.2 | 113.7 | 38% |

The champion acquires *more* fertilizer than any of them and applies the least.
The balance leaves through the market: 108 SELL orders a game name FERTILIZER,
and 304.5 units a game leave the shed that way.

It is not short of opportunities either. Across 12 games a unit stands on its
own unfertilized crop tile, on a turn the route left as PASS, 178.5 times a
game — but carries fertilizer on only 10.5 of them.

## What it changes

Two independent settings, both confined to turns the champion already wasted:

- `apply_on_pass` — on a PASS turn, if the unit carries fertilizer and stands on
  its own crop tile with `fertilized_until_day < day + 2`, emit `FERTILIZE`.
- `fertilizer_reserve` — keep N units back from SELL orders.
- `pickup_units` — on a PASS turn beside the shed, pick up N units.

No route step moves, no hand is added or removed, no order is added, and a unit
given real work keeps it. `apply_on_pass: false` with the other settings at 0
restores the champion exactly; the control arm returns 48 draws at margin 0.

It wraps root `main.py`, not `base/router.py`. The router runs at
`SALE_HORIZON` 2 and the promoted champion at 3 — a 3,630 coin/game packaging
difference that contaminated two earlier experiments in this slice — so the
control here is a provable no-op rather than an approximate one.

## Measured

Opponent root `main.py`, both seats. Screen = 6 seeds (12 games), holdout = 24
seeds (48 games). Seat 0 and seat 1 agree to the coin, so the panel is
deterministic and all margin is signal.

### Holdout, 48 games

| arm | W-D-L | points | margin | FERTILIZE/game |
| --- | --- | ---: | ---: | ---: |
| control | 0-48-0 | 0.500 | **+0** | 0 |
| **start_day 18** | **46-0-2** | **0.958** | **+203.8** | 5.54 |
| start_day 10 | 46-0-2 | 0.958 | +193.3 | 6.00 |

Zero errors, all statuses DONE, dead plants identical to control, no escaped
animals. Range −95 to +410; the only losing seed is 61007, on both seats.

### Screen, 12 games — start day

| start day | W-D-L | margin |
| ---: | --- | ---: |
| 0 | 8-0-4 | +44 |
| 2, 4 | 8-0-4 | +44 |
| 6, 8 | 12-0-0 | +135 |
| **10 – 18** | **12-0-0** | **+217** |
| 20 | 12-0-0 | +150 |
| 22, 24, 26 | 12-0-0 | +94 |

Monotone and readable: fertilizing before day 6 loses games outright, days 6–9
cost 82 coins, and the whole gain sits in days 18–19. Days 10–17 fire nothing,
so 10 and 18 are the same policy; **18 is chosen as the narrower of the two.**

### Falsified on the same harness, 12 games each

| arm | W-D-L | margin | why |
| --- | --- | ---: | --- |
| `pickup_units` 1 | 0-0-12 | −591 | walking to the shed costs more than the fertilizer returns |
| `pickup_units` 2 | 0-0-12 | −1,108 | as above, and 126 overflow units against 42 |
| `pickup_units` 5 | 0-0-12 | −1,828 | 270 overflow units; held fertilizer crowds out produce |
| `fertilizer_reserve` 40 | 0-0-12 | **−153,202** | see below |
| reserve 40 + apply + pickup | 0-0-12 | −153,211 | |
| reserve 100 + apply + pickup 10 | 0-0-12 | −153,206 | |
| reserve 40 from day 20 | 0-0-12 | −11,571 | 2,616 overflow units |
| reserve 60 from day 15 | 0-0-12 | −26,361 | 42 escaped animals |

**Withholding the fertilizer revenue destroys the agent.** Dropping 93 SELL
orders a game starves a HIRE the tape had budgeted for, so the hand never
arrives and the tape keeps issuing actions for it: 288 hand desyncs and 2,052
truncated hand actions per game, 238 dead plants against the control's 24, and
54 escaped animals. The −153k is that collapse, not an economic verdict on
fertilizer. It does establish the constraint that matters: **the champion cannot
stop selling its fertilizer, because its hiring schedule is budgeted on that
revenue, and a frozen tape has no way to notice the shortfall.**

## Scale

+204 coins on a ~50,000 coin score is 0.4%. The win rate is what makes it worth
keeping, not the size. 5.54 extra FERTILIZE actions a game are worth 204 coins,
about 37 coins each, and that is the whole of what the idle-turn budget can
reach. It does not close a 900-point leaderboard gap and nothing here suggests
it would.

## Promotion note

This changes unit actions on PASS turns only, but `FERTILIZE` is outside the
list `AGENTS.md` allows the adaptive layer to substitute (weed, water, feed).
Promoting it needs that constraint widened deliberately, not silently.

## Reproduce

```bash
.venv/bin/python benchmark.py \
  --agent agents/slices/kaggriculture-most-powerful-route/variants/fertilizer_use_v1/main.py \
  --opponent main.py --seeds $(seq 61000 61023) --both-seats \
  --params '{"_START_DAY":18,"_APPLY":true}'
```
