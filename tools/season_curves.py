"""Per-day farm economics for one cohort: where does a season's money come from?

Observer-only, and deliberately opponent-independent. Cash and final margin
depend on who you played; units harvested, units sold, tiles worked and coins
banked are counts on the agent's own board, so they compare across cohorts that
never met.

Money moves only through the market, so a per-step change decomposes cleanly:
positive is a filled SELL, negative is a BUY or a wage. A step that does both
nets, which undercounts both sides — it is a floor on gross flow, not an exact
split, and the sale-side floor is tight because buying and selling in the same
step is rare.

Shed deltas measure production the same way. Stock harvested into the shed on
the step it is sold nets out, so `harvested` is also a floor.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CROPS = ("WHEAT", "TOMATO", "CARROT", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")


def _tiles(farm: dict) -> Counter:
    return Counter(
        tile.get("animal") or tile.get("crop") or tile["kind"]
        for row in farm["tiles"] for tile in row if isinstance(tile, dict)
    )


def _shed(state: dict) -> dict:
    private = state["observation"].get("private") or {}
    return {k: int(v or 0) for k, v in (private.get("shed") or {}).items()}


def episode_curve(replay: dict, seat: int) -> dict:
    steps = replay["steps"]
    days: dict[int, dict] = defaultdict(lambda: {
        "revenue": 0.0, "spend": 0.0, "harvested": 0, "shed_out": 0,
        "hands_peak": 0, "field_ops": Counter(), "market_ops": Counter(),
    })

    for index, state in enumerate(steps):
        observation = state[seat]["observation"]
        day = int(observation["day"])
        record = days[day]
        farm = observation["farms"][seat]
        record["hands_peak"] = max(record["hands_peak"], len(farm.get("hands", [])))
        # End-of-day snapshot: last write for the day wins, so the terminal step
        # does not create a duplicate entry for the closing day.
        record["money_end"] = farm["money"]
        record["tiles_end"] = dict(_tiles(farm))
        record["quadrants_end"] = len(farm.get("unlocked_quadrants", []) or [])
        shed = _shed(state[seat])
        record["shed_units_end"] = sum(shed.values())
        prices = observation["market"]["prices"]
        record["shed_value_end"] = sum(q * prices.get(item, 0) for item, q in shed.items())

        if index + 1 >= len(steps):
            continue
        following = steps[index + 1]
        next_day = int(following[seat]["observation"]["day"])
        target = days[next_day]
        delta = following[seat]["observation"]["farms"][seat]["money"] - farm["money"]
        if delta > 0:
            target["revenue"] += delta
        else:
            target["spend"] += -delta
        next_shed = _shed(following[seat])
        for item in set(shed) | set(next_shed):
            change = next_shed.get(item, 0) - shed.get(item, 0)
            if change > 0:
                target["harvested"] += change
            else:
                target["shed_out"] += -change
        action = following[seat].get("action") or {}
        for unit in [action.get("farmer")] + list(action.get("hands") or []):
            if unit:
                target["field_ops"][unit[0]] += 1
        for order in action.get("market") or []:
            if order:
                target["market_ops"][order[0]] += 1

    ordered = [days[day] for day in sorted(days)]
    for record in ordered:
        record["field_ops"] = dict(record["field_ops"])
        record["market_ops"] = dict(record["market_ops"])
    rewards = replay.get("rewards") or [0, 0]
    return {
        "episode_id": replay["info"]["EpisodeId"], "seat": seat,
        "opponent": replay["info"]["TeamNames"][1 - seat],
        "final_margin": rewards[seat] - rewards[1 - seat],
        "final_score": rewards[seat],
        "days": ordered,
    }


DAY_FIELDS = ("money_end", "revenue", "spend", "harvested", "shed_out",
              "shed_units_end", "shed_value_end", "hands_peak", "quadrants_end")


def aggregate(curves: list[dict]) -> dict:
    length = min(len(item["days"]) for item in curves)
    per_day = []
    for day in range(length):
        records = [item["days"][day] for item in curves]
        entry = {"day": day}
        for field in DAY_FIELDS:
            entry[field] = statistics.mean(r.get(field, 0) for r in records)
        for group, names in (("field_ops", None), ("market_ops", None)):
            totals: Counter = Counter()
            for record in records:
                totals.update(record[group])
            entry[group] = {k: v / len(records) for k, v in totals.items()}
        for group, names in (("tiles", CROPS + ANIMALS + ("WEED", "PASTURE", "COOP", "EMPTY")),):
            entry["tiles"] = {name: statistics.mean(
                r.get("tiles_end", {}).get(name, 0) for r in records) for name in names}
        per_day.append(entry)

    def window(field, start, end):
        return per_day[end][field] - per_day[start][field] if end < len(per_day) else None

    def total(field, start, end):
        return sum(entry[field] for entry in per_day[start:end + 1])

    return {
        "episodes": len(curves),
        "mean_final_score": statistics.mean(item["final_score"] for item in curves),
        "mean_final_margin": statistics.mean(item["final_margin"] for item in curves),
        "per_day": per_day,
        "windows": {
            name: {
                "revenue": total("revenue", start, end),
                "spend": total("spend", start, end),
                "harvested": total("harvested", start, end),
                "sold": total("shed_out", start, end),
                "money_change": window("money_end", start, end),
                "tiles_change": {k: per_day[end]["tiles"][k] - per_day[start]["tiles"][k]
                                 for k in per_day[end]["tiles"]},
            }
            for name, (start, end) in
            (("d0_d10", (0, 10)), ("d10_d20", (10, 20)), ("d20_d29", (20, 29)),
             ("season", (0, min(29, len(per_day) - 1))))
        },
    }


def _from_snapshot(snapshot: str, team_filter: str | None):
    directory = ROOT / "experiments" / snapshot
    manifest = json.loads((directory / "manifest.json").read_text())
    raw = {int(item["episode_id"]): item for item in manifest["raw_files"]}
    teams = {int(t["team_id"]): t for t in manifest["cohort"]["teams"]}
    for association in sorted(manifest["cohort"]["associations"], key=lambda a: a["episode_id"]):
        team = teams[int(association["team_id"])]
        if team_filter and team["team_name"] != team_filter:
            continue
        record = raw[int(association["episode_id"])]
        yield team["team_name"], json.loads((ROOT / record["path"]).read_text()), int(association["seat"])


def _from_directory(directory: str, team: str):
    for path in sorted((ROOT / directory).glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        names = replay["info"]["TeamNames"]
        if team not in names:
            raise ValueError(f"{path.name} does not contain team {team!r}")
        yield team, replay, names.index(team)


def render(label: str, result: dict) -> None:
    print(f"\n===== {label} ({result['episodes']} episodes, "
          f"mean score {result['mean_final_score']:,.0f}) =====")
    print(f"{'day':>4}{'cash':>10}{'revenue':>10}{'spend':>10}{'harvest':>9}"
          f"{'sold':>8}{'shed':>7}{'hands':>7}{'quad':>6}")
    for entry in result["per_day"]:
        print(f"{entry['day']:>4}{entry['money_end']:>10,.0f}{entry['revenue']:>10,.0f}"
              f"{entry['spend']:>10,.0f}{entry['harvested']:>9,.0f}{entry['shed_out']:>8,.0f}"
              f"{entry['shed_units_end']:>7,.0f}{entry['hands_peak']:>7.1f}"
              f"{entry['quadrants_end']:>6.1f}")
    print(f"\n{'window':<10}{'revenue':>12}{'spend':>12}{'harvested':>12}{'sold':>12}{'cash change':>14}")
    for name, values in result["windows"].items():
        print(f"{name:<10}{values['revenue']:>12,.0f}{values['spend']:>12,.0f}"
              f"{values['harvested']:>12,.0f}{values['sold']:>12,.0f}"
              f"{values['money_change']:>14,.0f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot")
    source.add_argument("--replay-dir")
    parser.add_argument("--team", help="team name; required with --replay-dir")
    parser.add_argument("--label", default="cohort")
    parser.add_argument("--group-by-team", action="store_true",
                        help="snapshot only: one aggregate per team")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    if args.replay_dir and not args.team:
        parser.error("--replay-dir requires --team")

    cohort = (_from_snapshot(args.snapshot, None if args.group_by_team else args.team)
              if args.snapshot else _from_directory(args.replay_dir, args.team))
    grouped: dict[str, list] = defaultdict(list)
    for team_name, replay, seat in cohort:
        key = team_name if args.group_by_team else args.label
        grouped[key].append(episode_curve(replay, seat))

    results = {name: aggregate(curves) for name, curves in grouped.items()}
    for name in sorted(results, key=lambda k: -results[k]["mean_final_score"]):
        render(name, results[name])

    if args.output:
        path = ROOT / args.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
