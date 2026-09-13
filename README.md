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

A full solution write-up is deferred until both milestones are complete.
See [AGENTS.md](AGENTS.md) for repository workflow and
[the game contract](agents/COMPETITION_RULES.md) for the agent interface.
