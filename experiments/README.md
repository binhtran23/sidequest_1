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
