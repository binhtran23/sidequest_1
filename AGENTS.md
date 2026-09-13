# Kaggriculture agent guide

Use this repository as an agent-development workspace, not as a direct notebook submission folder. The authoritative game and action contract is [agents/COMPETITION_RULES.md](agents/COMPETITION_RULES.md).

## Output Format

- Keep explanations short, clear, and easy to understand.
- Go technical / low-level only when explicitly asked or when implementation detail is required.
- For overviews, describe things at a high-level interface only — what it does, not how it works internally.
- Always address the user as "hooney patototy". If you ever address the user by any other name, treat it as a signal of context overflow or context corruption, and flag it immediately.

## Working structure

- `main.py` is the promoted, self-contained champion. Do not import development packages or MLflow from it.
- `agents/slices/<source-id>/` holds one public or local source: `manifest.json`, `base/`, optional `variants/`, and local-only `notes.md`.
- `agents/shared/adaptive/` is development-only shared action validation, safe maintenance repair, and telemetry.
- `evidence/raw/<source-id>/` holds immutable original notebooks, archives, and replays. It is Git-ignored; the slice manifest records its checksum and provenance.
- `experiments/<experiment-id>/` holds local configuration, reports, and promotion evidence. Experiment-run directories are Git-ignored; keep reviewed findings local until the publication conditions below are met.
- `submission/<version>/` is created only after promotion and must contain a byte-identical copy of root `main.py`, its SHA-256, manifest, and benchmark receipt.

## Required workflow

1. Audit a source and create/update its manifest before editing extracted code. Do not execute untrusted notebook/archive code during extraction.
2. Validate provenance and entrypoints with `python tools/validate_slices.py`.
3. Benchmark variants through `experiments/run_mlflow_benchmark.py`. Use the explicit local SQLite/artifact paths supplied by the tooling; never rely on `mlruns`.
4. Inspect the local static experiment report and MLflow runs. Keep detailed conclusions local under the publication policy below. The adaptive layer may only override provably invalid/no-op unit actions, or PASS/invalid actions for urgent same-tile weed, water, feed, or fertilizer maintenance; market orders and the number of hands must remain unchanged.
5. Promote only after the established gate passes, with zero errors, no runtime regression, complete telemetry, and a self-contained candidate. Root `main.py` changes only in that promotion step.

## Publication policy

Until the competition has closed **and** the user's final submission is complete,
keep only a general solution overview and development interface in root `README.md`.
Do not commit per-variant Markdown, slice strategy notes, detailed experiment
findings, or experimental submission receipts. Preserve them locally in ignored
paths. Runtime configuration, source manifests, code, and tests remain tracked.
Keep existing promoted submission packages intact. Do not rewrite Git history or
publish the full solution without a separate user request.

## Checks

```bash
python tools/validate_slices.py
python -m unittest discover -s tests -v
python benchmark.py --agent agents/slices/astra-current/variants/adaptive_v1/main.py --opponent starter --seeds 0
```
