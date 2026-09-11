"""MLflow logging for a completed replay snapshot."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def log_snapshot(root: Path, experiment_dir: Path, manifest: dict, summary: dict) -> str:
    import mlflow

    database = root / ".local" / "mlflow" / "mlflow.db"
    artifacts = root / ".local" / "mlflow" / "artifacts"
    database.parent.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri("sqlite:///" + str(database))
    name = "kaggriculture.top_replays"
    existing = mlflow.get_experiment_by_name(name)
    experiment_id = existing.experiment_id if existing else mlflow.create_experiment(
        name, artifact_location=artifacts.resolve().as_uri()
    )
    prior = mlflow.MlflowClient().search_runs(
        [experiment_id],
        filter_string=(
            f"tags.snapshot_id = '{manifest['snapshot_id']}' and attributes.status = 'FINISHED'"
        ),
        max_results=1,
    )
    if prior:
        return prior[0].info.run_id
    by_team = {int(team["team_id"]): team for team in summary["teams"]}
    by_association = {item["association_id"]: item for item in summary["episodes"]}
    episodes_by_team = defaultdict(list)
    for association in manifest["cohort"]["associations"]:
        episodes_by_team[int(association["team_id"])].append(association)
    with mlflow.start_run(experiment_id=experiment_id, run_name=manifest["snapshot_id"]) as parent:
        mlflow.set_tag("snapshot_id", manifest["snapshot_id"])
        mlflow.log_params({
            "snapshot_id": manifest["snapshot_id"], "competition": manifest["cohort"]["competition"],
            "captured_at": manifest["cohort"]["captured_at"], "top": manifest["cohort"]["top"],
            "games_per_team": manifest["cohort"]["games_per_team"],
        })
        mlflow.log_metrics({
            "team_count": summary["team_count"],
            "episode_associations": summary["episode_associations"],
            "unique_replay_files": summary["unique_replay_files"],
        })
        for team_id in sorted(by_team, key=lambda item: by_team[item]["rank"]):
            team = by_team[team_id]
            with mlflow.start_run(run_name=f"team-rank-{team['rank']}", nested=True):
                mlflow.set_tags({"summary_level": "team", "team_id": team_id, "team_name": team["team_name"]})
                mlflow.log_params({"rank": team["rank"], "submission_id": team["submission_id"], "leaderboard_score": team["leaderboard_score"]})
                mlflow.log_metrics({
                    key: value for key, value in {
                        "episodes": team["episode_associations"], "wins": team["wins"],
                        "mean_reward": team["mean_reward"], "mean_route_efficiency": team["mean_route_efficiency"],
                        "movement_excess": team["movement_excess"], "idle_pass_rate": team["idle_pass_rate"],
                        "inferred_noop_rate": team["inferred_noop_rate"],
                        "tasks_per_shed_trip": team["tasks_per_shed_trip"],
                    }.items() if value is not None
                })
            for association in sorted(episodes_by_team[team_id], key=lambda item: item["episode_id"]):
                with mlflow.start_run(run_name=f"episode-{association['episode_id']}-team-{team_id}", nested=True):
                    episode = by_association[association["association_id"]]
                    mlflow.set_tags({
                        "summary_level": "episode", "team_id": team_id,
                        "episode_id": association["episode_id"], "seat": association["seat"],
                    })
                    mlflow.log_params({"submission_id": association["submission_id"], "opponent_team_name": association.get("opponent_team_name") or "unknown"})
                    mlflow.log_metrics({
                        key: value for key, value in {
                            "reward": episode["reward"], "opponent_reward": episode["opponent_reward"],
                            "mean_route_efficiency": episode["mean_route_efficiency"],
                            "movement_excess": episode["movement_excess"],
                            "idle_pass_rate": episode["idle_pass_rate"],
                            "inferred_noop_rate": episode["inferred_noop_rate"],
                            "task_count": episode["task_count"],
                        }.items() if value is not None
                    })
        for name in ("manifest.json", "summary.json", "report.html", "config.json"):
            candidate = experiment_dir / name
            if candidate.exists():
                mlflow.log_artifact(str(candidate), "snapshot")
        for parquet in sorted((experiment_dir / "raw").glob("*.parquet")):
            mlflow.log_artifact(str(parquet), "parquet")
        mlflow.set_tags({"observer_only": "true", "snapshot_status": manifest["status"]})
        return parent.info.run_id
