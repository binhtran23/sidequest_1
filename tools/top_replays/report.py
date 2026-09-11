"""Static hierarchical report for a completed top-replay snapshot."""
from __future__ import annotations

import html
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_summary(manifest: dict, tables: dict[str, list[dict]]) -> dict:
    by_team: dict[int, dict[str, Any]] = {}
    episodes_by_team: dict[int, list[dict]] = defaultdict(list)
    routes_by_team: dict[int, list[dict]] = defaultdict(list)
    routes_by_association: dict[str, list[dict]] = defaultdict(list)
    for row in tables["episodes"]:
        episodes_by_team[row["team_id"]].append(row)
    for row in tables["routes"]:
        routes_by_team[row["team_id"]].append(row)
        routes_by_association[row["association_id"]].append(row)
    for team in manifest["cohort"]["teams"]:
        team_id = int(team["team_id"])
        episodes = episodes_by_team[team_id]
        task_routes = [row for row in routes_by_team[team_id] if row["task_count"]]
        by_team[team_id] = {
            "rank": team["rank"], "team_id": team_id, "team_name": team["team_name"],
            "submission_id": team["submission_id"], "leaderboard_score": team["leaderboard_score"],
            "episode_associations": len(episodes),
            "wins": sum(row["result"] == "win" for row in episodes),
            "mean_reward": _mean([row["reward"] for row in episodes if row["reward"] is not None]),
            "mean_route_efficiency": _mean([row["route_efficiency_ratio"] for row in task_routes]),
            "movement_excess": sum(row["movement_excess"] for row in task_routes),
            "idle_pass_rate": _mean([row["idle_pass_rate"] for row in routes_by_team[team_id]]),
            "inferred_noop_rate": _mean([row["inferred_noop_rate"] for row in routes_by_team[team_id]]),
            "tasks_per_shed_trip": _mean([row["tasks_per_shed_trip"] for row in task_routes]),
            "exact_routes": sum(row["route_algorithm"] == "exact_dp" for row in task_routes),
            "approximate_routes": sum(row["route_algorithm"] == "insertion_2opt" for row in task_routes),
            "infeasible_routes": sum(not row["route_feasible"] for row in task_routes),
        }
    episode_summaries = []
    for episode in sorted(tables["episodes"], key=lambda row: (row["rank"], -row["episode_id"])):
        episode_routes = routes_by_association[episode["association_id"]]
        task_routes = [row for row in episode_routes if row["task_count"]]
        episode_summaries.append({
            "association_id": episode["association_id"], "episode_id": episode["episode_id"],
            "team_id": episode["team_id"], "seat": episode["seat"], "result": episode["result"],
            "reward": episode["reward"], "opponent_reward": episode["opponent_reward"],
            "mean_route_efficiency": _mean([row["route_efficiency_ratio"] for row in task_routes]),
            "movement_excess": sum(row["movement_excess"] for row in task_routes),
            "idle_pass_rate": _mean([row["idle_pass_rate"] for row in episode_routes]),
            "inferred_noop_rate": _mean([row["inferred_noop_rate"] for row in episode_routes]),
            "task_count": sum(row["task_count"] for row in task_routes),
        })
    return {
        "snapshot_id": manifest["snapshot_id"],
        "captured_at": manifest["cohort"]["captured_at"],
        "competition": manifest["cohort"]["competition"],
        "team_count": len(by_team),
        "episode_associations": len(tables["episodes"]),
        "unique_replay_files": len(manifest["raw_files"]),
        "table_rows": manifest.get("tables", {}),
        "teams": sorted(by_team.values(), key=lambda row: row["rank"]),
        "episodes": episode_summaries,
    }


def write_report(path: Path, manifest: dict, tables: dict[str, list[dict]]) -> dict:
    summary = build_summary(manifest, tables)
    routes: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    episodes_by_team: dict[int, list[dict]] = defaultdict(list)
    for row in tables["routes"]:
        routes[(row["association_id"], row["day"], row["unit_id"])].append(row)
    for row in tables["episodes"]:
        episodes_by_team[row["team_id"]].append(row)

    team_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(_fmt(team[key]))}</td>" for key in (
            "rank", "team_name", "leaderboard_score", "submission_id", "episode_associations",
            "mean_reward", "mean_route_efficiency", "movement_excess", "idle_pass_rate",
            "inferred_noop_rate", "tasks_per_shed_trip", "approximate_routes", "infeasible_routes",
        )) + "</tr>" for team in summary["teams"]
    )
    hierarchy = []
    for team in summary["teams"]:
        hierarchy.append(
            f"<details><summary>Rank {team['rank']} — {html.escape(team['team_name'])} "
            f"(submission {team['submission_id']})</summary>"
        )
        for episode in sorted(episodes_by_team[team["team_id"]], key=lambda row: row["episode_id"], reverse=True):
            hierarchy.append(
                f"<details><summary>Episode {episode['episode_id']} · seat {episode['seat']} · "
                f"{episode['result']} · reward {_fmt(episode['reward'])}</summary>"
            )
            episode_strategy = [row for row in tables["strategy_days"] if row["association_id"] == episode["association_id"]]
            for day_row in sorted(episode_strategy, key=lambda row: row["day"]):
                hierarchy.append(
                    f"<details><summary>Day {day_row['day']} · {html.escape(day_row['economic_phase'])} · "
                    f"money Δ {_fmt(day_row['money_delta'])} · tasks {day_row['field_tasks']}</summary><ul>"
                )
                unit_keys = sorted(
                    key for key in routes if key[0] == episode["association_id"] and key[1] == day_row["day"]
                )
                for key in unit_keys:
                    unit_routes = routes[key]
                    hierarchy.append(
                        f"<li>{html.escape(key[2])}: " + "; ".join(
                            f"chain {row['start_step']}–{row['end_step']}, tasks={row['task_count']}, "
                            f"actual/shadow={row['actual_movement']}/{row['shadow_movement']}, "
                            f"algorithm={row['route_algorithm']}"
                            for row in unit_routes
                        ) + "</li>"
                    )
                hierarchy.append("</ul></details>")
            hierarchy.append("</details>")
        hierarchy.append("</details>")

    columns = [
        "Rank", "Team", "Score", "Submission", "Games", "Mean reward", "Route efficiency",
        "Movement excess", "Idle/PASS", "Inferred no-op", "Tasks/shed trip", "Approx routes",
        "Infeasible routes",
    ]
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(summary['snapshot_id'])}</title>
<style>body{{font:14px system-ui,sans-serif;max-width:1400px;margin:2rem auto;padding:0 1rem;color:#202124}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{border:1px solid #ddd;padding:.4rem;text-align:right}}
th:nth-child(2),td:nth-child(2){{text-align:left}}details{{margin:.45rem 0 0 1rem}}summary{{cursor:pointer}}code{{background:#f4f4f4;padding:.1rem .25rem}}</style></head>
<body><h1>Top-team replay observer</h1>
<p>Snapshot <code>{html.escape(summary['snapshot_id'])}</code>, captured {html.escape(summary['captured_at'])}.
Observer-only: no policy action was executed or changed.</p>
<p>{summary['episode_associations']} team-game associations; {summary['unique_replay_files']} unique immutable replay files.</p>
<h2>Team comparison</h2><table><thead><tr>{''.join(f'<th>{item}</th>' for item in columns)}</tr></thead><tbody>{team_rows}</tbody></table>
<h2>Season → episode → daily plan → unit task chain</h2>{''.join(hierarchy)}
</body></html>"""
    path.write_text(document)
    return summary
