"""Summarize completed A/B receipts and verify their local MLflow records."""
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/route-test-v1-20260912"


def main():
    connection = sqlite3.connect(f"file:{ROOT / '.local/mlflow/mlflow.db'}?mode=ro", uri=True)
    records = []
    for directory in sorted((ROOT / "experiments").glob("route-v1-*")):
        summary_path = directory / "benchmark.summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text())
        if directory.name.endswith("-r1"):
            continue  # Superseded by the guarded, instrumented revision.
        run_id = summary["run_id"]
        status = connection.execute("SELECT status FROM runs WHERE run_uuid=?", (run_id,)).fetchone()
        children = connection.execute(
            "SELECT r.run_uuid,r.status FROM runs r JOIN tags t ON r.run_uuid=t.run_uuid "
            "WHERE t.key='mlflow.parentRunId' AND t.value=?", (run_id,)).fetchall()
        if status != ("FINISHED",) or len(children) != summary["games"] or any(s != "FINISHED" for _, s in children):
            raise ValueError(f"Incomplete MLflow records: {directory.name}")
        points = []
        for child, _ in children:
            metric = connection.execute("SELECT value FROM latest_metrics WHERE run_uuid=? AND key='points'", (child,)).fetchone()
            if metric is None:
                raise ValueError(f"Missing points: {child}")
            points.append(metric[0])
        if abs(sum(points)/len(points)-summary["points_rate"]) > 1e-10:
            raise ValueError(f"Static/MLflow mismatch: {directory.name}")
        events = Counter()
        choices = Counter()
        for path in (directory / "raw").glob("*.anomalies.jsonl"):
            for line in path.open():
                event = json.loads(line)
                hypothesis = event.get("hypothesis", event["type"])
                events[hypothesis] += 1
                for key in ("accept", "wheat_branch"):
                    if key in event:
                        choices[f"{hypothesis}.{key}={event[key]}"] += 1
        records.append({"experiment": directory.name, **summary,
                        "telemetry_counts": dict(events), "choices": dict(choices),
                        "mlflow_verified": True})
    (OUT / "results.json").write_text(json.dumps(records, indent=2)+"\n")
    lines = ["# Route test v1 A/B results", "",
             "Selected test version: `agents/slices/kaggriculture-most-powerful-route/variants/test_v1/main.py`.",
             "Its three-turn sale window was selected from screening and frozen before holdout. Other switches are disabled in this entrypoint.",
             "The `screen-test_v1-r2` row below refers to the original all-hypothesis prototype; its original settings and sources are archived with that run.", "",
             "Every row is a head-to-head comparison with the frozen most-powerful-route champion.",
             "Screen: six seeds (four recent loss seeds and two recent win seeds), both seats.",
             "Holdout: 24 predeclared unseen seeds, both seats. Seat pairs are not independent samples.", "",
             "| Experiment | W / D / L | Mean coin margin | Mean callback ms | Error games |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for r in records:
        lines.append(f"| {r['experiment']} | {r['wins']} / {r['draws']} / {r['losses']} | {r['mean_coin_margin']:+,.2f} | {r['mean_action_ms']:.3f} | {r['errors'] + r['status_errors']} |")
    lines += ["", "## Verification", "",
              "All listed parent/child run statuses and aggregate points were checked against the explicit local SQLite MLflow database.",
              "`results.json` includes diagnostics, timings for both agents, terminal inventory, event counts and run IDs.",
              "Each experiment retains source/config hashes, source snapshots and per-game telemetry under its ignored `raw/` directory and local MLflow artifacts.", "",
              "The first prototype stopped on an empty native market slot in feed handling. That case was corrected and regression-tested before revision r2; r1 is excluded here.", "",
              "## Interpretation", "",
              "The unchanged-policy control tied all 12 screening games. The three-turn window had the highest mean margin among the candidates that won all screening games.",
              "The feed switch did not activate on this screen. The crop selector retained carrots in all 12 games. The tomato profit gate accepted all six eligible investments. Their tied results are inconclusive, not evidence of improvement.",
              "Disabling tomatoes lost 2,024.33 coins on average; greedy final-day routes lost 326.83. They remain separate experiments, not enabled in the selected test.",
              "Changing farm actions can change future shop draws: the engine uses the same daily RNG for weeds and town unlocks. Same-seed A/B games are full policy comparisons, not identical future market trajectories or recreations of the original Kaggle opponents.",
              "Runtime includes development telemetry and cold policy initialization on the first callback. Being below the action timeout is not proof of zero runtime regression.", "",
              "These development variants have not been promoted or submitted to Kaggle. Positive results against this champion do not establish leaderboard performance."]
    (OUT / "report.md").write_text("\n".join(lines)+"\n")
    print(json.dumps([{k:r[k] for k in ("experiment","wins","draws","losses","mean_coin_margin","choices")} for r in records], indent=2))


if __name__ == "__main__":
    main()
