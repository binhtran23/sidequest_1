# Kaggriculture agent lab

A development workspace for agents competing in Kaggriculture.

## General approach

The agent combines planned farm routines with observation-based adjustments.
It coordinates workers, maintains crops and animals, manages limited resources,
and chooses when to convert production into sale revenue. Changes are evaluated
locally across multiple seeds and both player positions before promotion.

Root `main.py` is the self-contained, locally promoted champion. Experimental
agents live separately and are not automatically promoted by a Kaggle upload.

## Repository layout

- `main.py`: current local champion.
- `agents/slices/`: source provenance, base policies, and experimental variants.
- `agents/shared/`: development-only validation and telemetry.
- `benchmark.py`, `experiments/`, and `tools/`: evaluation and development tooling.
- `tests/`: regression checks.
- `submission/`: versioned promoted packages.

Configuration and source manifests stay in Git. Raw replays, generated reports,
local experiment data, and detailed strategy notes are not part of the public
development documentation.

## Local development

Use Python 3.11+ with `kaggle-environments` and the dependencies in
`requirements-dev.txt` installed in a virtual environment.

```bash
.venv/bin/python tools/validate_slices.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python benchmark.py --agent main.py --opponent starter --seeds 0
```

Provenance validation requires the original source evidence in the local
`evidence/raw/` directory. Benchmark reports and MLflow data remain local.

## Documentation policy

Until the competition has closed and the final submission is complete, this
README contains only the general approach and development interface. Per-variant
READMEs, detailed strategy notes, experiment findings, and experimental submission
receipts stay local and are excluded from new commits. Previously committed
documents may still be present in Git history.

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

A full solution write-up is deferred until both milestones are complete.
See [AGENTS.md](AGENTS.md) for repository workflow and
[the game contract](agents/COMPETITION_RULES.md) for the agent interface.
