#!/usr/bin/env python3
"""Rating-adjusted strength of our own submissions, measured on the real ladder.

Why this exists: the local benchmark scores a candidate against our own past
selves, and its effect sizes (+204 coins/game for route-v2-fert18) are far
inside the ladder's per-game spread (about +/-13,000 coins). Worse, a Kaggle
simulation rating climbs from a cold start, so comparing the public scores of
two submissions of different ages compares their ages, not their strength.

This tool reads the outcome of every completed public episode a submission has
played, grades each opponent by that team's leaderboard score, and reports win
rate per opponent-strength band plus the rating at which the submission wins
half its games. That equilibrium figure is comparable across submissions of
different ages, which the public score is not.

Read the caveat in the report: a low-rated submission meets high-scoring teams
mainly when those teams have just uploaded something, and a fresh upload may be
an experiment. Treat a band with few games as directional.

    python tools/ladder_report.py --submission 56199076 56187998
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.top_replays.api import (KaggleReplayClient, text_value,  # noqa: E402
                                   timestamp_value, value)

BANDS = [(0, 1800), (1800, 2100), (2100, 2300), (2300, 2450), (2450, 10000)]
LOGISTIC_SCALE = 400.0
BOOTSTRAP_SEED = 20260914


def episode_rows(episodes, submission_id: int) -> list[dict]:
    """One row per completed public episode this submission actually scored."""
    rows, seen = [], set()
    for episode in episodes:
        episode_id = int(value(episode, "id"))
        if episode_id in seen:
            continue
        state = (text_value(value(episode, "state")) or "").upper()
        if state and not state.endswith(("COMPLETED", "COMPLETE")):
            continue
        agents = value(episode, "agents", []) or []
        mine = [a for a in agents if int(value(a, "submission_id", -1)) == submission_id]
        theirs = [a for a in agents if int(value(a, "submission_id", -1)) != submission_id]
        if len(mine) != 1 or len(theirs) != 1:
            continue
        us, them = mine[0], theirs[0]
        our_reward, their_reward = value(us, "reward"), value(them, "reward")
        if our_reward is None or their_reward is None:
            continue
        seen.add(episode_id)
        rows.append({
            "episode_id": episode_id,
            "end_time": timestamp_value(value(episode, "end_time")) or "",
            "seat": int(value(us, "index", 0)),
            "coins": float(our_reward),
            "opponent_coins": float(their_reward),
            "margin": float(our_reward) - float(their_reward),
            "won": float(our_reward) > float(their_reward),
            "opponent_team_id": int(value(them, "team_id", 0)),
            "opponent_team_name": str(value(them, "team_name", "")),
            "opponent_submission_id": int(value(them, "submission_id", 0)),
        })
    rows.sort(key=lambda row: (row["end_time"], row["episode_id"]))
    return rows


def _graded(rows, ratings):
    return [(ratings[r["opponent_team_id"]], r) for r in rows if r["opponent_team_id"] in ratings]


def band_summary(rows, ratings, bands=BANDS) -> list[dict]:
    """Win rate and mean margin per opponent-strength band."""
    graded = _graded(rows, ratings)
    summary = []
    for low, high in bands:
        inside = [r for rating, r in graded if low <= rating < high]
        wins = sum(1 for r in inside if r["won"])
        summary.append({
            "band": [low, high],
            "games": len(inside),
            "wins": wins,
            "win_rate": wins / len(inside) if inside else None,
            "mean_margin": statistics.mean(r["margin"] for r in inside) if inside else None,
        })
    return summary


def equilibrium_rating(rows, ratings, scale=LOGISTIC_SCALE, bounded_only=False):
    """Opponent rating at which this submission wins exactly half its games.

    Solves sum(won - sigmoid((R - opponent) / scale)) = 0 for R. The sum falls
    monotonically in R, so bisection is exact and needs no learning rate. A
    record with no losses (or no wins) has no finite solution; that is reported
    as None under `bounded_only` and clamped to the search bound otherwise.
    """
    graded = _graded(rows, ratings)
    if not graded:
        return None
    def residual(rating):
        return sum(won - 1.0 / (1.0 + math.exp(-(rating - opponent) / scale))
                   for opponent, r in graded for won in (1.0 if r["won"] else 0.0,))
    low = min(rating for rating, _ in graded) - 4 * scale
    high = max(rating for rating, _ in graded) + 4 * scale
    if residual(low) < 0:
        return None if bounded_only else low
    if residual(high) > 0:
        return None if bounded_only else high
    for _ in range(200):
        middle = (low + high) / 2.0
        if residual(middle) > 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def bootstrap_equilibrium(rows, ratings, draws=2000, scale=LOGISTIC_SCALE):
    """Deterministic 95% resampling interval for the equilibrium rating."""
    graded = _graded(rows, ratings)
    if len(graded) < 2:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    plain = [r for _, r in graded]
    samples = []
    for _ in range(draws):
        estimate = equilibrium_rating(rng.choices(plain, k=len(plain)), ratings, scale)
        if estimate is not None:
            samples.append(estimate)
    if not samples:
        return None
    samples.sort()
    return [samples[int(0.025 * len(samples))], samples[min(len(samples) - 1, int(0.975 * len(samples)))]]


def load_ratings(path: Path) -> dict[int, float]:
    """Team id to public score, from a downloaded leaderboard CSV."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {int(row["TeamId"]): float(row["Score"]) for row in csv.DictReader(handle)}


def rank_for(score: float, ratings: dict[int, float]) -> int:
    ordered = sorted(ratings.values())
    return len(ordered) - bisect.bisect_right(ordered, score) + 1


def download_leaderboard(competition: str, destination: Path) -> Path:
    import subprocess
    import zipfile
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "kaggle", "competitions", "leaderboard",
                    competition, "--download", "-p", str(destination)],
                   check=True, capture_output=True)
    archive = destination / f"{competition}.zip"
    if archive.exists():
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(destination)
    latest = max(destination.glob("*publicleaderboard*.csv"), key=lambda p: p.stat().st_mtime)
    return latest


def report(submission_id: int, rows: list[dict], ratings: dict[int, float]) -> dict:
    point = equilibrium_rating(rows, ratings)
    graded = len(_graded(rows, ratings))
    return {
        "submission_id": submission_id,
        "episodes": len(rows),
        "episodes_graded": graded,
        "window": [rows[0]["end_time"], rows[-1]["end_time"]] if rows else None,
        "wins": sum(1 for r in rows if r["won"]),
        "losses": sum(1 for r in rows if not r["won"]),
        "win_rate": statistics.mean(1.0 if r["won"] else 0.0 for r in rows) if rows else None,
        "mean_margin": statistics.mean(r["margin"] for r in rows) if rows else None,
        "margin_stdev": statistics.pstdev([r["margin"] for r in rows]) if len(rows) > 1 else None,
        "equilibrium_rating": point,
        "equilibrium_95": bootstrap_equilibrium(rows, ratings),
        "implied_rank": rank_for(point, ratings) if point is not None else None,
        "bands": band_summary(rows, ratings),
    }


def render(reports: list[dict], ratings: dict[int, float]) -> str:
    lines = ["# Ladder report", "",
             f"Graded against {len(ratings):,} leaderboard teams.", ""]
    for entry in reports:
        lines += [f"## Submission {entry['submission_id']}", "",
                  f"{entry['episodes']} episodes, {entry['wins']}-{entry['losses']}, "
                  f"mean margin {entry['mean_margin']:+,.0f} "
                  f"(per-game stdev {entry['margin_stdev'] or 0:,.0f}).", ""]
        if entry["equilibrium_rating"] is not None:
            interval = entry["equilibrium_95"]
            span = f", 95% [{interval[0]:,.0f}, {interval[1]:,.0f}]" if interval else ""
            lines.append(f"**Equilibrium rating {entry['equilibrium_rating']:,.0f}**"
                         f"{span} — implied rank ~{entry['implied_rank']:,}.")
        else:
            lines.append("Equilibrium rating is unbounded on this record.")
        lines += ["", "| Opponent band | Games | Win rate | Mean margin |",
                  "| --- | ---: | ---: | ---: |"]
        for band in entry["bands"]:
            low, high = band["band"]
            if not band["games"]:
                continue
            lines.append(f"| {low}–{high} | {band['games']} | "
                         f"{band['win_rate']:.0%} | {band['mean_margin']:+,.0f} |")
        lines.append("")
    lines += ["## Caveat", "",
              "A submission climbs from a cold start, so a young one has faced weaker",
              "opposition than its band table suggests, and it meets high-scoring teams",
              "mainly when those teams have themselves just uploaded. Read a band with",
              "few games as directional and re-run once the submission has converged.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--submission", type=int, nargs="+", required=True)
    parser.add_argument("--competition", default="kaggriculture")
    parser.add_argument("--leaderboard", help="existing public leaderboard CSV; downloaded when omitted")
    parser.add_argument("--output", default="experiments/ladder-report")
    args = parser.parse_args(argv)

    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    csv_path = Path(args.leaderboard) if args.leaderboard else \
        download_leaderboard(args.competition, output / "leaderboard")
    ratings = load_ratings(csv_path)

    client = KaggleReplayClient()
    reports, episodes = [], {}
    for submission_id in args.submission:
        rows = episode_rows(client.submission_episodes(submission_id), submission_id)
        episodes[str(submission_id)] = rows
        reports.append(report(submission_id, rows, ratings))

    (output / "episodes.json").write_text(json.dumps(episodes, indent=2) + "\n")
    (output / "ladder.json").write_text(json.dumps(
        {"leaderboard_csv": csv_path.name, "teams": len(ratings), "reports": reports},
        indent=2) + "\n")
    (output / "report.md").write_text(render(reports, ratings))
    print(render(reports, ratings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
