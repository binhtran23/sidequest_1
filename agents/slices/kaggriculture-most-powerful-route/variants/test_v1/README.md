# Route test v1

Selected setting: `sale_horizon = 3` (champion: 2).

The three-turn sale window won all 12 screening games, with a mean advantage of
3,630.17 coins against the champion. It beat the tested pressure-aware sale
rule, their combination, and the initial combination of all five hypotheses.
The setting was frozen before the predeclared 24-seed holdout.

Holdout result: 48 wins / 0 draws / 0 losses across 24 seeds in both seats;
mean advantage 3,985.58 coins, zero runtime/status errors. Mean callback time
was 0.196 ms versus the champion's 0.188 ms. All 21 repository tests passed.
The current source/config hashes match the frozen holdout receipt.

`main.py` is the development entrypoint. `settings.json` chooses enabled
experiments; `policy.py` contains all five switches for the sibling ablations.
The original all-switch configuration is retained in the screen experiment's
source snapshot under `experiments/route-v1-screen-test_v1-r2/raw/sources/`.

Results and selection rationale: `experiments/route-test-v1-20260912/`.
This is not a promoted or self-contained Kaggle submission.
