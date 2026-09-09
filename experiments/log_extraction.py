"""Log static source-extraction evidence without importing extracted code."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_slices import validate_slice


def main():
    import mlflow

    db = ROOT / ".local" / "mlflow" / "mlflow.db"
    artifacts = ROOT / ".local" / "mlflow" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri("sqlite:///" + str(db))
    name = "kaggriculture.extraction"
    experiment = mlflow.get_experiment_by_name(name)
    experiment_id = experiment.experiment_id if experiment else mlflow.create_experiment(name, artifact_location=artifacts.resolve().as_uri())
    for path in sorted((ROOT / "agents" / "slices").iterdir()):
        if not (path / "manifest.json").is_file():
            continue
        manifest = json.loads((path / "manifest.json").read_text())
        result = validate_slice(path)
        with mlflow.start_run(experiment_id=experiment_id, run_name=manifest["source_id"]):
            mlflow.log_params({
                "source_id": manifest["source_id"], "source_type": manifest["source_type"],
                "source_url": manifest.get("source_url", manifest.get("origin_path", "")),
                "raw_sha256": manifest["raw_sha256"], "extractor_version": manifest["extractor_version"],
                "entrypoint": manifest["entrypoint"], "extraction_status": manifest["extraction_status"],
                "static_validation": manifest["static_validation"],
            })
            receipt = ROOT / "experiments" / "refactor-baseline" / f"extraction-{manifest['source_id']}.json"
            receipt.write_text(json.dumps(result, indent=2))
            mlflow.log_artifact(str(receipt), "receipts")


if __name__ == "__main__":
    main()
