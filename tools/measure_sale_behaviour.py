"""Compare how two agents actually transact: order size, fill, and price timing.

Observer-only. Order quantity alone is misleading, because the engine clamps a
SELL to the seller's holdings; an order of 1000 against a 100-item shed is a
sell-everything sentinel, not a large trade. This measures ordered units, units
that actually leave the shed, and where in each product's own price range the
sale was placed.

Units leaving the shed are a lower bound: stock harvested into the shed on the
same step nets against the measured decrease.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _from_snapshot(snapshot: str):
    manifest = json.loads((ROOT / "experiments" / snapshot / "manifest.json").read_text())
    seats = {int(item["episode_id"]): int(item["seat"])
             for item in manifest["cohort"]["associations"]}
    for record in manifest["raw_files"]:
        episode_id = int(record["episode_id"])
        yield json.loads((ROOT / record["path"]).read_text()), seats[episode_id]


def _from_directory(directory: str, team: str):
    for path in sorted((ROOT / directory).glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        names = replay["info"]["TeamNames"]
        if team not in names:
            raise ValueError(f"{path.name} does not contain team {team!r}")
        yield replay, names.index(team)


def _sell_batch(action) -> dict[str, int]:
    batch: dict[str, int] = defaultdict(int)
    for order in (action or {}).get("market", []) or []:
        if order and order[0] == "SELL" and len(order) > 2:
            try:
                batch[order[1]] += int(order[2])
            except (TypeError, ValueError):
                continue
    return batch


def measure(cohort, limit: int | None = None) -> dict:
    ordered: dict[str, int] = defaultdict(int)
    filled: dict[str, int] = defaultdict(int)
    quantities: dict[str, list[int]] = defaultdict(list)
    percentiles: dict[str, list[float]] = defaultdict(list)
    selling_steps = []
    processed = 0
    for index, (replay, seat) in enumerate(cohort):
        if limit is not None and index >= limit:
            break
        processed += 1
        steps = replay["steps"]
        series: dict[str, list[float]] = defaultdict(list)
        for state in steps:
            for item, price in state[seat]["observation"]["market"]["prices"].items():
                series[item].append(price)
        used = set()
        for i in range(len(steps) - 1):
            prices = steps[i][seat]["observation"]["market"]["prices"]
            shed = steps[i][seat]["observation"]["private"]["shed"]
            following = steps[i + 1][seat]["observation"]["private"]["shed"]
            for item, quantity in _sell_batch(steps[i + 1][seat]["action"]).items():
                if item not in prices:
                    continue
                used.add(i)
                ordered[item] += quantity
                quantities[item].append(quantity)
                held = int(shed.get(item, 0) or 0)
                filled[item] += max(held - int(following.get(item, 0) or 0), 0)
                values = series[item]
                percentiles[item].append(
                    sum(1 for value in values if value < prices[item]) / len(values))
        selling_steps.append(len(used))
    return {
        "episodes": processed, "selling_steps_per_game": statistics.mean(selling_steps),
        "products": {item: {
            "orders": len(quantities[item]),
            "median_quantity": statistics.median(quantities[item]),
            "mean_quantity": statistics.mean(quantities[item]),
            "units_ordered": ordered[item], "units_left_shed": filled[item],
            "fill_ratio": filled[item] / max(ordered[item], 1),
            "mean_price_percentile": statistics.mean(percentiles[item]),
        } for item in sorted(quantities, key=lambda key: -ordered[key])},
        "total_units_ordered": sum(ordered.values()),
        "total_units_left_shed": sum(filled.values()),
        "overall_fill_ratio": sum(filled.values()) / max(sum(ordered.values()), 1),
        "overall_price_percentile": statistics.mean(
            [value for values in percentiles.values() for value in values]),
    }


def render(name: str, result: dict) -> None:
    print(f"\n===== {name} ({result['episodes']} episodes) =====")
    print(f"selling steps per game: {result['selling_steps_per_game']:.1f} | "
          f"overall fill ratio: {result['overall_fill_ratio']:.4f} | "
          f"mean price percentile: {result['overall_price_percentile']:.3f}")
    print(f"{'product':<12}{'orders':>8}{'med qty':>9}{'mean qty':>10}"
          f"{'ordered':>10}{'left shed':>11}{'fill':>8}{'price pct':>11}")
    for item, values in result["products"].items():
        print(f"{item:<12}{values['orders']:>8}{values['median_quantity']:>9.0f}"
              f"{values['mean_quantity']:>10.1f}{values['units_ordered']:>10}"
              f"{values['units_left_shed']:>11}{values['fill_ratio']:>8.4f}"
              f"{values['mean_price_percentile']:>11.3f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="frozen snapshot id under experiments/")
    parser.add_argument("--replay-dir", help="loose replay directory")
    parser.add_argument("--team", help="team name; required with --replay-dir")
    parser.add_argument("--label", default="cohort")
    parser.add_argument("--limit", type=int, help="use only the first N episodes")
    parser.add_argument("--output", help="write the measurement as JSON")
    args = parser.parse_args(argv)
    if not args.snapshot and not args.replay_dir:
        parser.error("pass --snapshot or --replay-dir")
    if args.replay_dir and not args.team:
        parser.error("--replay-dir requires --team")

    cohort = (_from_snapshot(args.snapshot) if args.snapshot
              else _from_directory(args.replay_dir, args.team))
    result = measure(cohort, args.limit)
    render(args.label, result)
    if args.output:
        path = ROOT / args.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"label": args.label, **result}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
