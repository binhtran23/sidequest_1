# Kaggriculture agent lab

This repository develops, evaluates, and promotes Kaggriculture competition agents. The root `main.py` is the current champion submission; development code never changes it until a promotion gate passes.

To enter the competition, accept the rules and submit through the [Kaggriculture competition overview](https://www.kaggle.com/competitions/kaggriculture/overview).

## Current champion

`submission/route-v2-fert18-20260912/` — a tape-driven router that picks one of 13 frozen
season-long action tapes from the first two shops it observes, then layers weed repair, a
three-turn sale window, a tomato investment, and terminal liquidation on top. It replaced
`route-v1-h3-20260912` on 2026-09-12 after winning **46 of 48 holdout games at +203.8
coins a game**, both seats, zero errors, no runtime regression.

The change it carries is `V227`, and it came out of measuring the top five's replays
against our own. On the inputs that were supposed to explain the gap, the champion is not
behind: over days 0–10 it out-earns every top-5 team, buys more land, and reaches day 12
with tiles and animals matched to the rank-1 agent. It then harvests 541 units over days
10–20 against that agent's 878.

The one production input that separates them is fertilizer. The champion acquires 343.8
units a game — more than any of the top five — and applies 67.7, fewer than any of them.
It cannot simply stop selling the balance: its hiring schedule is budgeted 719 turns in
advance on that revenue, and withholding it costs 153,202 coins a game. `V227` therefore
spends only what a unit already carries, on its own tile, on a turn the route had already
left idle. That is worth 5.54 applications a game and +204 coins — real and repeatable,
and about 0.4% of a season's score. It does not close the gap to the leaderboard's top,
and the evidence says nothing reachable from a frozen tape would.

Full write-ups: `experiments/season-curves-20260912/report.md` (the measurement),
`experiments/fertilizer-use-20260912/` (the A/B and everything falsified alongside it),
`experiments/leader-route-20260912/report.md` and `experiments/rank-gradient-20260912/`
(why the leaders' routes cannot be copied at all).

## Repository layout

```text
.
├── main.py                         # current self-contained champion submission
├── AGENTS.md                       # development constraints and workflow
├── requirements-dev.txt            # MLflow development dependency
├── benchmark.py                    # local game runner and diagnostics
├── agents/
│   ├── COMPETITION_RULES.md        # local agent I/O and gameplay reference
│   ├── shared/adaptive/            # safe action guard and telemetry
│   └── slices/<source-id>/
│       ├── manifest.json           # source provenance and checksums
│       ├── base/                   # editable extracted base policy
│       ├── variants/               # development-only policy variants
│       └── notes.md
├── evidence/raw/<source-id>/       # immutable raw source; Git-ignored
├── experiments/
│   ├── run_mlflow_benchmark.py     # reproducible benchmark runner
│   ├── log_extraction.py           # extraction provenance logger
│   └── <experiment-id>/            # local run outputs; Git-ignored
├── tools/
│   ├── validate_slices.py          # static provenance/entrypoint checks
│   └── init_mlflow.py              # local MLflow experiment setup
└── submission/<version>/           # created only by successful promotion
```

`agents/slices` contains editable extractions. Every slice manifest records the upstream identity, checksum, extractor version, and entrypoint. Raw notebooks, archives, and replays remain immutable under `evidence/raw` and are not committed.

## Setup and run

Use Python 3.11+ and install the local game environment plus development dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -U pip kaggle-environments
.venv/bin/python -m pip install -r requirements-dev.txt
```

Verify source provenance and run the focused test suite:

```bash
.venv/bin/python tools/validate_slices.py
.venv/bin/python -m unittest discover -s tests -v
```

Run one complete local season against Kaggle's built-in starter agent:

```bash
.venv/bin/python benchmark.py \
  --agent agents/slices/astra-current/variants/adaptive_v1/main.py \
  --opponent starter --seeds 0 \
  --output /tmp/kaggriculture-smoke.json
```

To run the current root champion instead, use `--agent main.py`. The root agent remains self-contained and does not require MLflow at submission time.

## How evaluation works

`benchmark.py` runs a full Kaggriculture season for every requested seed and seat. It reports points, final coin margin, candidate/opponent coins, action latency, errors, plant/animal loss, shed overflow, terminal inventory, and adaptive override events.

- Use a fixed seed panel and `--both-seats` for an unbiased comparison across player positions.
- Use `--diagnostics` to collect engine no-op, plant-loss, animal-loss, and overflow diagnostics.
- Use `--replay <path>` only when a replay is needed for debugging; do not commit generated replay payloads by default.
- Treat a short starter-agent smoke test as a health check, not performance evidence. Promotion evidence requires the configured multi-seed, both-seat benchmark and report review.

## MLflow evaluation

Initialize the explicit local SQLite backend and log extraction provenance:

```bash
.venv/bin/python tools/init_mlflow.py
.venv/bin/python experiments/log_extraction.py
.venv/bin/python experiments/run_mlflow_benchmark.py \
  --experiment-id refactor-baseline --both-seats
```

The benchmark creates one parent run and one nested run per game in `kaggriculture.benchmark`. The parent stores immutable source/base hashes, Git SHA, resolved configuration, opponent, frozen seed panel, and seat policy. Nested runs log game metrics and anomaly events. Reports, receipts, raw outputs, SQLite metadata, and MLflow artifacts stay local for review. Once a result is accepted for publication, summarize it for readers in this README rather than committing the generated experiment payloads.

Open the local UI with:

```bash
.venv/bin/mlflow ui \
  --backend-store-uri "sqlite:///$PWD/.local/mlflow/mlflow.db" \
  --default-artifact-root "file://$PWD/.local/mlflow/artifacts"
```

## Development workflow

1. Add or audit a source slice and run `python tools/validate_slices.py`. Extraction is static only; it never executes untrusted notebook code.
2. Implement a variant under the source slice. The adaptive wrapper may repair only provably invalid/no-op unit actions or urgent same-tile maintenance — weed, water, feed, or fertilizer; it does not alter market orders or the number of hands.
3. Run the local benchmark and review its experiment receipt plus MLflow telemetry locally. Add only approved conclusions to this README.
4. Require static validation, adaptive parity tests, zero benchmark errors, no runtime regression, and receipt review before promotion. Only then may a self-contained candidate create `submission/<version>/` and replace root `main.py` byte-for-byte.

## Submission

After promotion creates a versioned submission artifact, submit its self-contained `main.py` through Kaggle:

```bash
kaggle competitions submit kaggriculture \
  -f submission/<version>/main.py \
  -m "<version and benchmark summary>"
```

Do not submit a slice base/variant directly and do not replace root `main.py` outside the promotion workflow.

For the current game rules and agent I/O contract, see [the agent rules reference](agents/COMPETITION_RULES.md). For development instructions, see [AGENTS.md](AGENTS.md).
