# Experiments

Committed experiment folders contain resolved input configuration, reports, and promotion registry records. Large runtime output belongs under `experiments/<id>/raw/` and is ignored. MLflow metadata and artifacts are local-only under `.local/mlflow/`.

```bash
pip install -r requirements-dev.txt
python tools/init_mlflow.py
python experiments/log_extraction.py
python experiments/run_mlflow_benchmark.py --experiment-id refactor-baseline --both-seats
mlflow ui --backend-store-uri "sqlite:///$PWD/.local/mlflow/mlflow.db" --default-artifact-root "file://$PWD/.local/mlflow/artifacts"
```

The benchmark runner uses absolute paths internally; the UI command is the only command that depends on the shell's current directory.

## Top-team replay observer

After authenticating the Kaggle CLI and accepting the competition rules, capture
the leaderboard atomically and collect each selected submission's latest 15
completed public games:

```bash
kaggle auth login
python tools/collect_top_replays.py --competition kaggriculture --top 3 --games-per-team 15
```

The generated `experiments/top-replays-*/manifest.json`, `config.json`,
`summary.json`, and `report.html` are compact and may be committed. Immutable
replays live under ignored `evidence/raw/<snapshot-id>/`; derived Parquet files
live under ignored `experiments/<snapshot-id>/raw/`. To resume without changing
the frozen cohort, pass the printed `--snapshot-id`. Existing evidence must
match its manifest checksum and is never downloaded or replaced on a rerun.

Use `--capture-only` to stop after evidence acquisition or `--skip-mlflow` for a
local normalization/report run that does not create tracking runs. The observer
never imports, executes, or modifies `main.py`.
