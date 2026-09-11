"""Initialize the three local Kaggriculture MLflow experiments explicitly."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / ".local" / "mlflow" / "mlflow.db"
ARTIFACTS = ROOT / ".local" / "mlflow" / "artifacts"


def main():
    import mlflow

    DB.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri("sqlite:///" + str(DB))
    artifact_uri = ARTIFACTS.resolve().as_uri()
    for name in (
        "kaggriculture.extraction",
        "kaggriculture.benchmark",
        "kaggriculture.promotion",
        "kaggriculture.top_replays",
    ):
        if not mlflow.get_experiment_by_name(name):
            mlflow.create_experiment(name, artifact_location=artifact_uri)
        print(name)


if __name__ == "__main__":
    main()
