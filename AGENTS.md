# Kaggriculture agent guide

Use this repository as an agent-development workspace, not as a direct notebook submission folder. The authoritative game and action contract is [agents/COMPETITION_RULES.md](agents/COMPETITION_RULES.md).

## Working structure

- `main.py` is the promoted, self-contained champion. Do not import development packages or MLflow from it.
- `agents/slices/<source-id>/` holds one public or local source: `manifest.json`, `base/`, optional `variants/`, and `notes.md`.
- `agents/shared/adaptive/` is development-only shared action validation, safe maintenance repair, and telemetry.
- `evidence/raw/<source-id>/` holds immutable original notebooks, archives, and replays. It is Git-ignored; the slice manifest records its checksum and provenance.
- `experiments/<experiment-id>/` holds committed configuration, reports, and promotion records. Large runtime data belongs in its ignored `raw/` directory.
- `submission/<version>/` is created only after promotion and must contain a byte-identical copy of root `main.py`, its SHA-256, manifest, and benchmark receipt.

## Required workflow

1. Audit a source and create/update its manifest before editing extracted code. Do not execute untrusted notebook/archive code during extraction.
2. Validate provenance and entrypoints with `python tools/validate_slices.py`.
3. Benchmark variants through `experiments/run_mlflow_benchmark.py`. Use the explicit local SQLite/artifact paths supplied by the tooling; never rely on `mlruns`.
4. Inspect the static experiment report and local MLflow runs. The adaptive layer may only override provably invalid/no-op unit actions, or PASS/invalid actions for urgent same-tile weed, water, or feed maintenance; market orders and the number of hands must remain unchanged.
5. Promote only after the established gate passes, with zero errors, no runtime regression, complete telemetry, and a self-contained candidate. Root `main.py` changes only in that promotion step.

## Checks

```bash
python tools/validate_slices.py
python -m unittest discover -s tests -v
python benchmark.py --agent agents/slices/astra-current/variants/adaptive_v1/main.py --opponent starter --seeds 0
```
