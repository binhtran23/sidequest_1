# shop_plan_probe — shop-pair coverage, falsified

Development probe. **No alternative plan improves on the champion's default. Do not
promote.** Retained as evidence and as a control harness for future plan work.

## Hypothesis

`SHOP_PLANS` has 15 keys and every one of them contains `YARN_STORE`. Openings are drawn
from roughly 64 ordered pairs, so most games fall through to plan 0: measured over two
15-episode cohorts on 2026-09-12, only 6 of 15 of the leader's games and 4 of 15 of our
own hit a key. Filling that gap — routing uncovered openings to a better continuation —
should be worth coins, and needs no leader data.

This probe replaces `SHOP_PLANS` with a lookup that ignores the observed pair and returns
one fixed plan, so each of the 13 continuations can be scored on openings the table does
not cover. Only the selection at `ROUTE_STEP` 144 is overridden; the forced switch to
plan 2 at `FINAL_PLAN_STEP` and every repair, sale and liquidation rule are untouched.

## Control

With no plan forced and `sale_horizon` 3, the probe returns **12 draws and a margin of
exactly 0** against root `main.py` — it reproduces the champion bit for bit. Every number
below is therefore signal, not variance.

All six route-test-v1 screen seeds fall through to plan 0, which makes them exactly the
population this hypothesis is about:

| Seed | Opening pair |
| --- | --- |
| 785985614 | PET_CAFE \| BAKERY |
| 2080455400 | BAKERY \| BAKERY |
| 458333647 | PIZZA_SHOP \| FARMERS_MARKET |
| 1669076510 | PET_CAFE \| SMOOTHIE_SHOP |
| 56669821 | FARMERS_MARKET \| BAKERY |
| 825367279 | SMOOTHIE_SHOP \| BRUNCH_SPOT |

## Result

Six seeds, both seats, opponent root `main.py`.

| Plan | Wins | Draws | Mean margin | Dead plants | Overflow |
| ---: | ---: | ---: | ---: | ---: | ---: |
| **0** (default) | 0 | **12** | **+0** | 24 | 42 |
| 2 | 2 | 0 | −968 | 24 | 42 |
| 10 | 2 | 0 | −8,208 | 24 | 12 |
| 4 | 0 | 0 | −10,235 | 24 | 0 |
| 5 | 0 | 0 | −10,440 | 24 | 0 |
| 7 | 0 | 0 | −10,891 | 24 | 30 |
| 8 | 0 | 0 | −10,931 | 24 | 30 |
| 6 | 0 | 0 | −11,088 | 24 | 30 |
| 11 | 0 | 0 | −11,113 | 24 | 30 |
| 3 | 0 | 0 | −11,291 | 24 | 30 |
| 1 | 0 | 0 | −11,510 | 24 | 0 |
| 9 | 0 | 0 | −12,010 | 12 | 378 |
| 12 | 0 | 0 | −18,319 | 0 | 8 |

Per seed, plan 0 is best on five of six. On the sixth (2080455400) plan 2 wins by **63
coins** — well inside anything worth acting on, and plan 2 is the endgame continuation,
which would be a strange choice to run from step 144.

## Conclusion

The fall-through is not a gap; **plan 0 is the correct default for uncovered openings.**

Plans 1 and 3–12 are continuations searched and tuned for yarn-market openings. Applied
to a non-yarn opening they cost 8,000–18,000 coins per game. That is also the likely
reason the table contains only `YARN_STORE` keys: the alternatives were never general
continuations, and routing more pairs into them would make the agent worse, not better.

Extending coverage would require *new* tapes searched against non-yarn openings, which is
a tape-search project rather than a re-keying of the existing table.

## Reproduce

```bash
# control: must return 12 draws, margin 0
echo '{"sale_horizon":3}' > settings.json
.venv/bin/python benchmark.py \
  --agent agents/slices/kaggriculture-most-powerful-route/variants/shop_plan_probe/main.py \
  --opponent main.py --both-seats \
  --seeds 785985614 2080455400 458333647 1669076510 56669821 825367279
# then set {"force_plan": N, "sale_horizon": 3} for N in 0..12
```

Receipts: `experiments/leader-route-20260912/shop-plan-sweep/plan-NN.json`.

**Note for any variant wrapping `base/router.py`:** root `main.py` is that router with
`SALE_HORIZON` 2 → 3 applied by `tools/build_route_submission.py`. A variant that does
not set the horizon to 3 runs 3,630 coins per game behind the champion on this panel for
packaging reasons alone. Always confirm a no-op control returns 12 draws before reading
any arm.
