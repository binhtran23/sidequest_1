"""Which observable behaviours vary monotonically with leaderboard standing?

Observer-only. Groups a multi-team snapshot by team, derives the same per-episode
metrics `analyze_leader_routes` uses, and ranks each team-level metric by its
Spearman correlation with leaderboard score.

With a handful of teams only near-perfect monotonicity means anything: for five
teams and no ties a perfect ordering gives rho 1.0 at a one-tailed p of about
0.017, and one swapped pair already drops it to 0.9. Treat this as a filter for
what deserves a benchmark, never as evidence on its own.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.analyze_leader_routes import analyze, digest, tape_determinism

ANIMALS = ("GOOSE", "COW", "SHEEP")


# The day series samples every 24 steps AND the terminal step, so the final day
# appears twice (steps 696 and 719). Take the last match: one sample per day, and
# the closing day reads the true end state. Summing every entry and dividing by
# the episode count instead double-counts that day.
def _assets_on(episode: dict, day: int) -> dict:
    matches = [e["assets"][episode["seat"]] for e in episode["days"] if e["day"] == day]
    return matches[-1] if matches else {}


def _cash_on(episode: dict, day: int) -> float | None:
    matches = [e["money"][episode["seat"]] for e in episode["days"] if e["day"] == day]
    return matches[-1] if matches else None


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def team_metrics(episodes: list[dict], tapes: dict[int, list]) -> dict:
    def asset(day, *names):
        return _mean([sum(_assets_on(e, day).get(n, 0) for n in names) for e in episodes])

    wheat10, animals10 = asset(10, "WHEAT"), asset(10, *ANIMALS)
    cows20, cows29 = asset(20, "COW"), asset(29, "COW")
    determinism = tape_determinism(tapes) if len(tapes) > 1 else {}
    return {
        "episodes": len(episodes),
        "win_rate": sum(1 for e in episodes if e["result"] == "win") / len(episodes),
        "mean_final_margin": _mean([e["final_margin"] for e in episodes]),
        "mean_peak_hands": _mean([e["mean_peak_hands"] for e in episodes]),
        "mean_hires": _mean([e["hires"] for e in episodes]),
        "mean_route_efficiency": _mean(
            [e["route_health"].get("mean_route_efficiency") for e in episodes]),
        "disruption_excess": _mean([e["disruption_excess"] for e in episodes]),
        "wheat_tiles_d10": wheat10,
        "animals_d10": animals10,
        "animals_per_wheat_d10": (animals10 / wheat10) if wheat10 else None,
        "geese_d10": asset(10, "GOOSE"),
        "strawberry_d10": asset(10, "STRAWBERRY"),
        "cows_d20": cows20,
        "cows_d29": cows29,
        "late_cow_growth": (cows29 - cows20) if (cows20 is not None and cows29 is not None) else None,
        "pastures_d29": asset(29, "PASTURE"),
        "weeds_d29": asset(29, "WEED"),
        "cash_d5": _mean([_cash_on(e, 5) for e in episodes]),
        "cash_d10": _mean([_cash_on(e, 10) for e in episodes]),
        "cash_d20": _mean([_cash_on(e, 20) for e in episodes]),
        "cash_d29": _mean([_cash_on(e, 29) for e in episodes]),
        "distinct_shop_pairs": len({tuple(e["shop_pair"]) for e in episodes}),
        "first_unit_divergence": determinism.get("earliest_unit_divergence_step"),
        "unit_divergence_fraction": determinism.get("mean_unit_divergence_fraction"),
    }


def _ranks(values: list[float]) -> list[float]:
    """Average ranks, ties shared."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2 + 1
        for k in range(i, j + 1):
            result[order[k]] = shared
        i = j + 1
    return result


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return num / (dx * dy) if dx and dy else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", default="experiments/rank-gradient")
    args = parser.parse_args(argv)

    snapshot_dir = ROOT / "experiments" / args.snapshot
    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    if manifest["status"] != "complete" or manifest.get("failures"):
        raise ValueError(f"snapshot {args.snapshot} is not a complete, failure-free capture")
    summary = json.loads((snapshot_dir / "summary.json").read_text())
    raw = {int(item["episode_id"]): item for item in manifest["raw_files"]}
    teams = {int(t["team_id"]): t for t in manifest["cohort"]["teams"]}

    grouped = defaultdict(list)
    for association in manifest["cohort"]["associations"]:
        grouped[int(association["team_id"])].append(association)

    per_team = {}
    for team_id, associations in grouped.items():
        episodes, tapes = [], {}
        for association in sorted(associations, key=lambda a: a["episode_id"]):
            record = raw[int(association["episode_id"])]
            path = ROOT / record["path"]
            if digest(path) != record["sha256"]:
                raise ValueError(f"frozen evidence changed: {path}")
            item = analyze(path, association, summary)
            tapes[item["episode_id"]] = item.pop("_tape")
            episodes.append(item)
        team = teams[team_id]
        per_team[team_id] = {
            "rank": team["rank"], "team_name": team["team_name"],
            "leaderboard_score": float(team["leaderboard_score"]),
            "submission_id": team["submission_id"],
            "metrics": team_metrics(episodes, tapes),
        }
        print(f"analysed rank {team['rank']}: {team['team_name']}", flush=True)

    ordered = sorted(per_team.values(), key=lambda t: t["rank"])
    scores = [t["leaderboard_score"] for t in ordered]
    names = [key for key in ordered[0]["metrics"] if
             all(t["metrics"].get(key) is not None for t in ordered)]

    correlations = []
    for key in names:
        values = [t["metrics"][key] for t in ordered]
        if len(set(values)) < 2:
            continue
        rho = spearman(scores, values)
        if rho is not None:
            correlations.append((abs(rho), rho, key, values))
    correlations.sort(reverse=True)

    width = max(len(k) for _, _, k, _ in correlations) + 2
    print("\nteams by leaderboard score: " + ", ".join(
        f"{t['team_name']} {t['leaderboard_score']}" for t in ordered))
    print("\n" + "metric".ljust(width) + "rho".rjust(7) +
          "".join(f"#{t['rank']}".rjust(12) for t in ordered))
    for _, rho, key, values in correlations:
        cells = "".join(format(v, ",.3f").rjust(12) if abs(v) < 100
                        else format(v, ",.0f").rjust(12) for v in values)
        print(key.ljust(width) + format(rho, "+.2f").rjust(7) + cells)

    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "rank-gradient.json").write_text(json.dumps({
        "snapshot_id": manifest["snapshot_id"],
        "captured_at": manifest["cohort"]["captured_at"],
        "teams": ordered,
        "correlations": [{"metric": k, "spearman_rho": r, "values_by_rank": v}
                         for _, r, k, v in correlations],
    }, indent=2) + "\n")
    print(f"\nwrote {(output / 'rank-gradient.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
