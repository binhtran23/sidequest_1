#!/usr/bin/env python3
"""Measure the days 18-30 conversion deficit that decides our games.

Measured 2026-09-14 over 15 replays against teams rated 2400-2950: through day
18 we are level or ahead and the farms are physically indistinguishable (57.0
against 57.0 crops, 17.0 against 17.5 animals). Then, in losses, days 18-30
bring in 46,820 against their 57,408 while we spend 2,006 less. The endgame is
not the cause -- we led at step 696 in 0 of 10 losses.

The mechanism is market saturation. Price is almost perfectly inverse to market
inventory (rho -0.95 to -0.995 across MILK, WOOL, STRAWBERRY and CARROT), and in
losses the opponent realises 1.31x that item's median late-season price against
our 1.14x. A fixed tape schedule cannot see the market filling up.

This tool turns that into a repeatable number so a candidate can be judged on
whether it closes the gap, not just on coins. Point it at downloaded replays:

    python tools/conversion_gap.py --replays evidence/raw/<snapshot> --team "<name>"
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TURNS_PER_DAY = 24
WINDOW_START_DAY = 18
WINDOW_START = WINDOW_START_DAY * TURNS_PER_DAY
SIDES = ("ours", "theirs")


def margin_at(game, step: int) -> float:
    money = game["money"]
    ours, theirs = money[min(step, len(money) - 1)]
    return ours - theirs


def cash_flows(game, start: int, end: int) -> dict:
    """Gross cash in and out for each side across [start, end)."""
    money = game["money"]
    end = min(end, len(money) - 1)
    flows = {side: {"inflow": 0.0, "outflow": 0.0} for side in SIDES}
    for step in range(max(0, start), max(0, end)):
        for index, side in enumerate(SIDES):
            delta = money[step + 1][index] - money[step][index]
            if delta > 0:
                flows[side]["inflow"] += delta
            else:
                flows[side]["outflow"] -= delta
    return flows


def sale_quality(game, window_start: int) -> dict:
    """How well each side timed its sales, priced against the item's own median.

    A value above 1.0 means the side sold when that good was dearer than usual,
    which is the same as saying it sold when the market held less of it.
    """
    medians = game["medians"]
    scored = {side: [] for side in SIDES}
    for step, side, item, price in game["sales"]:
        median = medians.get(item, 0.0)
        if step < window_start or median <= 0 or side not in scored:
            continue
        scored[side].append(price / median)
    return {side: {"events": len(values),
                   "mean_relative_price": statistics.mean(values) if values else None,
                   "share_below_median": (sum(1 for v in values if v < 1) / len(values)
                                          if values else None)}
            for side, values in scored.items()}


def summarise_game(game, window_start: int = WINDOW_START) -> dict:
    last = len(game["money"]) - 1
    flows = cash_flows(game, window_start, last)
    return {
        "final_margin": margin_at(game, last),
        "margin_at_window_start": margin_at(game, window_start),
        "won": margin_at(game, last) > 0,
        "flows": flows,
        "inflow_gap": flows["ours"]["inflow"] - flows["theirs"]["inflow"],
        "outflow_gap": flows["ours"]["outflow"] - flows["theirs"]["outflow"],
        "sale_quality": sale_quality(game, window_start),
        "opponent": game.get("opponent"),
    }


def _cohort(rows) -> dict:
    if not rows:
        return {"games": 0}
    def mean(key):
        return statistics.mean(r[key] for r in rows)
    def relative(side):
        values = [r["sale_quality"][side]["mean_relative_price"] for r in rows
                  if r["sale_quality"][side]["mean_relative_price"] is not None]
        return statistics.mean(values) if values else None
    return {
        "games": len(rows),
        "mean_final_margin": mean("final_margin"),
        "mean_margin_at_window_start": mean("margin_at_window_start"),
        "mean_inflow_gap": mean("inflow_gap"),
        "mean_outflow_gap": mean("outflow_gap"),
        "mean_inflow_ours": statistics.mean(r["flows"]["ours"]["inflow"] for r in rows),
        "mean_inflow_theirs": statistics.mean(r["flows"]["theirs"]["inflow"] for r in rows),
        "sale_quality_ours": relative("ours"),
        "sale_quality_theirs": relative("theirs"),
    }


def aggregate(summaries) -> dict:
    return {"wins": _cohort([s for s in summaries if s["won"]]),
            "losses": _cohort([s for s in summaries if not s["won"]]),
            "all": _cohort(list(summaries))}


def load_replay(path: Path, team: str) -> dict | None:
    """Normalise one Kaggle replay into the structure the metrics operate on."""
    replay = json.loads(path.read_text())
    names = replay.get("info", {}).get("TeamNames") or []
    if team not in names:
        return None
    ours = names.index(team)
    theirs = 1 - ours

    def observation(entry):
        for slot in entry:
            candidate = slot.get("observation") or {}
            if "farms" in candidate:
                return candidate
        return None

    money, sales, series = [], [], collections.defaultdict(list)
    for step, entry in enumerate(replay["steps"]):
        state = observation(entry)
        if state is None:
            money.append(money[-1] if money else (0.0, 0.0))
            continue
        money.append((float(state["farms"][ours]["money"]),
                      float(state["farms"][theirs]["money"])))
        prices = state.get("market", {}).get("prices", {})
        if step >= WINDOW_START:
            for item, price in prices.items():
                series[item].append(float(price))
        for index, side in ((ours, "ours"), (theirs, "theirs")):
            if index >= len(entry):
                continue
            for order in (entry[index].get("action") or {}).get("market") or []:
                if isinstance(order, list) and len(order) >= 2 and order[0] == "SELL":
                    price = prices.get(order[1])
                    if price:
                        sales.append((step, side, order[1], float(price)))
    return {"money": money, "sales": sales,
            "medians": {item: statistics.median(v) for item, v in series.items() if v},
            "opponent": names[theirs], "episode": replay.get("id")}


def render(report: dict) -> str:
    lines = ["# Late-season conversion gap", "",
             f"Window: day {WINDOW_START_DAY} to the end (step {WINDOW_START}+).", "",
             "| Cohort | Games | Margin at day 18 | Final margin | Our inflow | Their inflow | Gap |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name in ("losses", "wins"):
        row = report[name]
        if not row["games"]:
            continue
        lines.append(f"| {name} | {row['games']} | {row['mean_margin_at_window_start']:+,.0f} | "
                     f"{row['mean_final_margin']:+,.0f} | {row['mean_inflow_ours']:,.0f} | "
                     f"{row['mean_inflow_theirs']:,.0f} | {row['mean_inflow_gap']:+,.0f} |")
    lines += ["", "Sale timing, as a multiple of each good's own median late-season price",
              "(higher is better; price is inverse to market inventory):", "",
              "| Cohort | Ours | Theirs |", "| --- | ---: | ---: |"]
    for name in ("losses", "wins"):
        row = report[name]
        if not row["games"] or row["sale_quality_ours"] is None:
            continue
        lines.append(f"| {name} | {row['sale_quality_ours']:.3f}x | "
                     f"{row['sale_quality_theirs']:.3f}x |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replays", required=True, help="directory of episode-*-replay.json")
    parser.add_argument("--team", required=True, help="our team name as it appears in the replay")
    parser.add_argument("--output", default="experiments/conversion-gap")
    args = parser.parse_args(argv)

    summaries = []
    for path in sorted(Path(args.replays).glob("*.json")):
        game = load_replay(path, args.team)
        if game is None:
            continue
        summaries.append({**summarise_game(game), "episode": game["episode"]})
    if not summaries:
        print(f"no replays for team {args.team!r} in {args.replays}", file=sys.stderr)
        return 1

    report = aggregate(summaries)
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "conversion.json").write_text(
        json.dumps({"report": report, "games": summaries}, indent=2) + "\n")
    (output / "report.md").write_text(render(report))
    print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
