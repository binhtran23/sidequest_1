"""Reproducible full-season benchmarks and game-engine diagnostics.

Examples:
  .venv/bin/python benchmark.py --seeds 0 1 2 3 --opponent starter
  .venv/bin/python benchmark.py --seeds 0 1 2 3 --opponent main.py
"""

import argparse
import importlib.util
import inspect
import json
import statistics
import time
from collections import Counter
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as engine


def percentile(values, q):
    """Linear percentile without an extra dependency."""
    values = sorted(values)
    if not values:
        return 0.0
    index = (len(values) - 1) * q
    low, high = int(index), min(len(values) - 1, int(index) + 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def load_agent(path, suffix=""):
    spec = importlib.util.spec_from_file_location("entry_" + suffix, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_game(
    path,
    opponent,
    seed,
    seat=0,
    configuration=None,
    diagnostics=False,
    replay=None,
    parameters=None,
):
    module = load_agent(path, "us")
    if parameters:
        for key, value in parameters.items():
            setattr(module, key, value)
    other_durations = []
    if opponent.endswith(".py"):
        other_module = load_agent(opponent, "them")
        other_agent = other_module.agent
        takes_config = len(inspect.signature(other_agent).parameters) > 1

        def other(obs, config):
            start = time.perf_counter()
            try:
                return other_agent(obs, config) if takes_config else other_agent(obs)
            finally:
                other_durations.append(time.perf_counter() - start)

    else:
        other = opponent
    cfg = {"seed": seed, **(configuration or {})}
    env = make("kaggriculture", configuration=cfg, debug=True)
    durations, days, counts, telemetry_events = [], [], Counter(), []
    hires_by_day = {}
    original_plants = engine._daily_refresh_plants
    original_animals = engine._daily_refresh_animals
    original_drop = engine._drop_inventories_to_shed
    original_action = engine._apply_unit_action
    tracked_farm = [None]
    tracked_private = [None]
    current_player = [-1]
    issues, current_step = [], [0]

    def plants(farm, day, tpd):
        dying = [
            (x, y)
            for y, row in enumerate(farm["tiles"])
            for x, tile in enumerate(row)
            if isinstance(tile, dict)
            and tile.get("kind") == "PLANT"
            and not tile["watered_today"]
            and tile["consecutive_unwatered"] >= 1
        ]
        original_plants(farm, day, tpd)
        if farm is tracked_farm[0]:
            counts["dead_plants"] += len(dying)
            if dying:
                issues.append({"day": day, "dead_plants": dying})

    def animals(farm, day):
        dying = sum(
            1
            for row in farm["tiles"]
            for tile in row
            if isinstance(tile, dict)
            and tile.get("animal")
            and not tile["fed_today"]
            and tile["consecutive_unfed"] >= 1
        )
        original_animals(farm, day)
        if farm is tracked_farm[0]:
            counts["escaped_animals"] += dying
            if dying:
                issues.append({"day": day, "escaped_animals": dying})

    def drop(private, capacity):
        total = sum(private["shed"].values()) + sum(
            sum(inv.values()) for inv in private["inventories"]
        )
        if private is tracked_private[0]:
            counts["overflow_units"] += max(0, total - capacity)
            if total > capacity:
                issues.append({"step": current_step[0], "overflow": total - capacity})
        return original_drop(private, capacity)

    def action(farm, private, idx, act, *args, **kwargs):
        # Identify the live engine objects; observations are copied by the runner.
        if idx == 0:
            current_player[0] = (current_player[0] + 1) % 2
        if current_player[0] == seat:
            tracked_farm[0], tracked_private[0] = farm, private
        if (
            diagnostics
            and farm is tracked_farm[0]
            and act
            and act[0] not in ("PASS", *engine.FARMER_MOVES)
        ):
            position = engine._farmer_position(farm, idx)
            before = (
                json.dumps([farm["tiles"][position[1]][position[0]], private])
                if position
                else None
            )
            result = original_action(farm, private, idx, act, *args, **kwargs)
            after = (
                json.dumps([farm["tiles"][position[1]][position[0]], private])
                if position
                else None
            )
            counts["op_" + act[0]] += 1
            if before == after:
                counts["noop_" + act[0]] += 1
                issues.append({"step": current_step[0], "noop": act, "pos": position})
            return result
        return original_action(farm, private, idx, act, *args, **kwargs)

    def ours(obs, config):
        current_step[0] = obs.step
        day = int(obs.day)
        hires_by_day[day] = max(
            hires_by_day.get(day, 0), int(obs.farms[seat].get("hires_today", 0))
        )
        start = time.perf_counter()
        result = module.agent(obs, config)
        durations.append(time.perf_counter() - start)
        drain = getattr(module, "drain_telemetry", None)
        if drain:
            telemetry_events.extend(drain())
        assert len(result["market"]) <= config.maxMarketOrdersPerTurn
        assert len(result["hands"]) == len(obs.farms[seat]["hands"])
        if obs.hour == 0:
            farm = obs.farms[seat]
            assets = Counter(
                tile.get("crop", tile.get("animal", tile["kind"]))
                for row in farm["tiles"]
                for tile in row
                if isinstance(tile, dict)
            )
            plan = getattr(module, "_STATE", {}).get(seat, {})
            days.append(
                {
                    "day": obs.day,
                    "money": farm["money"],
                    "assets": dict(assets),
                    "workers": plan.get("workers"),
                    "urgent_skipped_selection": plan.get(
                        "urgent_skipped_selection", 0
                    ),
                    "urgent_skipped_final": plan.get("urgent_skipped_final", 0),
                    "timed_net_value": plan.get("timed_net_value"),
                    "prices": dict(obs.market["prices"]),
                    "shed": dict(obs.private["shed"]),
                }
            )
        return result

    agents = [other, other]
    agents[seat] = ours
    engine._daily_refresh_plants, engine._daily_refresh_animals = plants, animals
    engine._drop_inventories_to_shed, engine._apply_unit_action = drop, action
    start = time.perf_counter()
    try:
        env.run(agents)
    finally:
        engine._daily_refresh_plants, engine._daily_refresh_animals = (
            original_plants,
            original_animals,
        )
        engine._drop_inventories_to_shed, engine._apply_unit_action = (
            original_drop,
            original_action,
        )
    final = env.steps[-1]
    own, their = final[seat], final[1 - seat]
    inv = own.observation.private
    hires_by_day[int(final[seat].observation.day)] = max(
        hires_by_day.get(int(final[seat].observation.day), 0),
        int(final[seat].observation.farms[seat].get("hires_today", 0)),
    )
    multiplier = cfg.get("farmHandCostMult", 1)
    fib = [1, 1]
    for _ in range(22):
        fib.append(fib[-1] + fib[-2])
    wages = sum(sum(fib[:n]) * multiplier for n in hires_by_day.values())
    draw = own.reward == their.reward if own.reward is not None else False
    result = {
        "seed": seed,
        "seat": seat,
        "opponent": opponent,
        "scores": [s.reward for s in final],
        "our_score": own.reward,
        "opponent_score": their.reward,
        "status": [s.status for s in final],
        "win": own.reward > their.reward
        if own.reward is not None and their.reward is not None
        else False,
        "draw": draw,
        "points": 0.5 if draw else float(own.reward > their.reward),
        "coin_margin": own.reward - their.reward
        if own.reward is not None and their.reward is not None
        else None,
        "wages": wages,
        "hires_by_day": hires_by_day,
        "wall_seconds": round(time.perf_counter() - start, 3),
        "max_action_ms": round(1000 * max(durations, default=0), 3),
        "mean_action_ms": round(1000 * statistics.mean(durations), 3),
        "p95_action_ms": round(1000 * percentile(durations, 0.95), 3),
        "opponent_max_action_ms": round(
            1000 * max(other_durations, default=0), 3
        ),
        "opponent_mean_action_ms": round(
            1000 * statistics.mean(other_durations) if other_durations else 0, 3
        ),
        "diagnostics": dict(counts),
        "planner_metrics": dict(getattr(module, "_METRICS", {})),
        "final_shed": dict(inv["shed"]),
        "final_carried": sum(sum(v.values()) for v in inv["inventories"]),
        "shops": list(final[0].observation.town["unlocked_shops"]),
        "days": days,
        "errors": [log for logs in env.logs for log in logs if log.get("stderr")],
        "issues": issues,
        "telemetry_events": telemetry_events,
    }
    if replay:
        Path(replay).write_text(json.dumps(env.toJSON()))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="main.py")
    parser.add_argument("--opponent", default="starter")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(8)))
    parser.add_argument("--both-seats", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--config", default="{}")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--output", default="benchmark_results.json")
    parser.add_argument("--replay")
    args = parser.parse_args()
    results = []
    for seed in args.seeds:
        for seat in [0, 1] if args.both_seats else [0]:
            result = run_game(
                args.agent,
                args.opponent,
                seed,
                seat,
                json.loads(args.config),
                args.diagnostics,
                args.replay,
                json.loads(args.params),
            )
            results.append(result)
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in result.items()
                        if k not in ("days", "errors", "issues")
                    }
                ),
                flush=True,
            )
    summary = {
        "games": len(results),
        "wins": sum(r["win"] for r in results),
        "draws": sum(r["draw"] for r in results),
        "points_rate": statistics.mean(r["points"] for r in results),
        "mean_coins": statistics.mean(r["our_score"] for r in results),
        "mean_coin_margin": statistics.mean(r["coin_margin"] for r in results),
        "mean_wages": statistics.mean(r["wages"] for r in results),
        "dead_plants": sum(r["diagnostics"].get("dead_plants", 0) for r in results),
        "escaped_animals": sum(
            r["diagnostics"].get("escaped_animals", 0) for r in results
        ),
        "overflow_units": sum(
            r["diagnostics"].get("overflow_units", 0) for r in results
        ),
        "urgent_skipped_selection": sum(
            r.get("planner_metrics", {}).get("urgent_skipped_selection", 0)
            for r in results
        ),
        "urgent_skipped_final": sum(
            r.get("planner_metrics", {}).get("urgent_skipped_final", 0)
            for r in results
        ),
        "min_coins": min(r["our_score"] for r in results),
        "max_action_ms": max(r["max_action_ms"] for r in results),
    }
    Path(args.output).write_text(
        json.dumps({"summary": summary, "games": results}, indent=2)
    )
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
