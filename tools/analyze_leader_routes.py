"""Observe one frozen leader replay cohort; never alter an agent or replay.

Replay state t contains the action from callback t-1, so observation[t] pairs
with action[t+1] exactly as the champion-loss analyser does. Losses are ranked
beside wins: a route we transplant carries whatever weakness produced them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_STEP = 144
TURNS_PER_DAY = 24


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assets(farm: dict) -> dict:
    return dict(Counter(
        tile.get("animal") or tile.get("crop") or tile["kind"]
        for row in farm["tiles"] for tile in row if isinstance(tile, dict)
    ))


def _orders(action) -> list:
    return (action or {}).get("market", []) if isinstance(action, dict) else []


def _route_health(summary: dict, episode_id: int) -> dict:
    for item in summary.get("episodes", []):
        if int(item["episode_id"]) == episode_id:
            return {key: item[key] for key in (
                "mean_route_efficiency", "movement_excess", "idle_pass_rate",
                "inferred_noop_rate", "task_count",
            ) if key in item}
    return {}


def analyze(path: Path, association: dict, summary: dict) -> dict:
    replay = json.loads(path.read_text())
    seat = int(association["seat"])
    steps = replay["steps"]
    margins, days, events = [], [], []
    sales = [Counter(), Counter()]
    hires = [0, 0]
    hand_counts = []
    # Hands are rehired every morning, so hour 0 always reads zero. Peak hands
    # within each day is the labour signal; the hour-0 sample is not.
    peak_hands = defaultdict(int)

    for step, states in enumerate(steps):
        observation = states[seat]["observation"]
        farms = observation["farms"]
        margins.append(farms[seat]["money"] - farms[1 - seat]["money"])
        hand_counts.append(len(farms[seat].get("hands", [])))
        peak_hands[step // TURNS_PER_DAY] = max(
            peak_hands[step // TURNS_PER_DAY], hand_counts[-1])
        if step % TURNS_PER_DAY == 0 or step == len(steps) - 1:
            days.append({
                "step": step, "day": observation["day"],
                "margin": margins[-1],
                "money": [farm["money"] for farm in farms],
                "hands": [len(farm.get("hands", [])) for farm in farms],
                "assets": [assets(farm) for farm in farms],
                "prices": observation["market"]["prices"],
                "shops": observation["town"]["unlocked_shops"],
                "sale_requested_cumulative": [dict(item) for item in sales],
            })
        if step + 1 == len(steps):
            continue
        following = steps[step + 1]
        for player in (0, 1):
            for order in _orders(following[player]["action"]):
                if not order:
                    continue
                if order[0] == "SELL":
                    try:
                        sales[player][order[1]] += int(order[2])
                    except (ValueError, TypeError, IndexError):
                        sales[player][str(order[1]) + "_non_numeric"] += 1
                elif order[0] == "HIRE":
                    hires[player] += 1
            if step % TURNS_PER_DAY != TURNS_PER_DAY - 1:
                continue
            before = farms[player]
            after = following[player]["observation"]["farms"][player]
            for y, row in enumerate(before["tiles"]):
                for x, tile in enumerate(row):
                    if not isinstance(tile, dict):
                        continue
                    new = after["tiles"][y][x]
                    if tile.get("animal") and (not isinstance(new, dict) or not new.get("animal")):
                        events.append({"step": step + 1, "seat": player, "event": "animal_removed",
                                       "asset": tile["animal"], "tile": [x, y]})
                    if tile.get("crop") and isinstance(new, dict) and new.get("kind") == "WEED":
                        events.append({"step": step + 1, "seat": player, "event": "crop_to_weed",
                                       "asset": tile["crop"], "tile": [x, y]})

    rewards = replay["rewards"]
    final_margin = rewards[seat] - rewards[1 - seat]
    permanent = next((i for i in range(len(margins)) if max(margins[i:]) < 0), None)
    first_24 = next((i for i in range(len(margins) - 23) if max(margins[i:i + 24]) < 0), None)
    erosion = [{"from_step": a["step"], "to_step": b["step"], "margin_change": b["margin"] - a["margin"]}
               for a, b in zip(days, days[1:])]
    own_events = Counter(item["event"] for item in events if item["seat"] == seat)
    opponent_events = Counter(item["event"] for item in events if item["seat"] != seat)
    result = "win" if final_margin > 0 else ("loss" if final_margin < 0 else "draw")
    return {
        "episode_id": int(association["episode_id"]), "seat": seat,
        "opponent": replay["info"]["TeamNames"][1 - seat],
        "opponent_submission_id": association.get("opponent_submission_id"),
        "seed": replay["info"].get("seed"), "module_version": replay.get("module_version"),
        "statuses": replay.get("statuses"), "result": result,
        "rewards": rewards, "final_margin": final_margin,
        "shop_pair": steps[ROUTE_STEP][seat]["observation"]["town"]["unlocked_shops"][:2],
        "final_shops": days[-1]["shops"],
        "first_24_turn_deficit": first_24, "permanent_deficit_step": permanent,
        "worst_day_erosion": min(erosion, key=lambda item: item["margin_change"]),
        "best_day_gain": max(erosion, key=lambda item: item["margin_change"]),
        "hires": hires[seat], "opponent_hires": hires[1 - seat],
        "peak_hands_by_day": {str(day): count for day, count in sorted(peak_hands.items())},
        "mean_peak_hands": sum(peak_hands.values()) / len(peak_hands),
        "sales_requested": dict(sales[seat]),
        "opponent_sales_requested": dict(sales[1 - seat]),
        # Weeds and removed animals are ordinary churn (harvest, sale, day-end
        # weeding), not proof of a broken route. Only the gap against the
        # opponent in the same game carries information.
        "day_boundary_events": dict(own_events),
        "opponent_day_boundary_events": dict(opponent_events),
        "disruption_excess": sum(own_events.values()) - sum(opponent_events.values()),
        "route_health": _route_health(summary, int(association["episode_id"])),
        "days": days, "margins": margins, "erosion": erosion,
        "path": str(path.relative_to(ROOT)), "sha256": digest(path),
        # observation[t] -> action[t+1]; 719 callbacks, matching one action tape.
        "_tape": [steps[index + 1][seat]["action"] for index in range(len(steps) - 1)],
    }


def tape_determinism(tapes: dict[int, list]) -> dict:
    """Test whether a fixed action tape could reproduce this agent.

    A tape-driven agent emits identical actions until the step where its plan
    selection can differ. An agent whose unit actions diverge across episodes
    long before that is reacting to state no tape carries.
    """
    ids = sorted(tapes)
    reference = tapes[ids[0]]
    comparisons = []
    for episode_id in ids[1:]:
        tape = tapes[episode_id]
        length = min(len(tape), len(reference))
        unit_steps = [
            index for index in range(length)
            if tape[index].get("farmer") != reference[index].get("farmer")
            or tape[index].get("hands") != reference[index].get("hands")
        ]
        market_steps = sum(
            1 for index in range(length)
            if tape[index].get("market") != reference[index].get("market"))
        comparisons.append({
            "episode_id": episode_id,
            "first_unit_divergence_step": unit_steps[0] if unit_steps else None,
            "unit_action_steps_differing": len(unit_steps),
            "market_order_steps_differing": market_steps,
            "unit_divergence_fraction": len(unit_steps) / length,
        })
    firsts = [item["first_unit_divergence_step"] for item in comparisons
              if item["first_unit_divergence_step"] is not None]
    return {
        "reference_episode_id": ids[0],
        "earliest_unit_divergence_step": min(firsts) if firsts else None,
        "mean_unit_divergence_fraction": sum(
            item["unit_divergence_fraction"] for item in comparisons) / len(comparisons),
        "comparisons": comparisons,
    }


def aggregate(results: list[dict]) -> dict:
    record = Counter(item["result"] for item in results)
    per_opponent: dict[str, Counter] = defaultdict(Counter)
    for item in results:
        per_opponent[item["opponent"]][item["result"]] += 1
    pairs = Counter(tuple(item["shop_pair"]) for item in results)
    losses = [item for item in results if item["result"] != "win"]
    return {
        "episodes": len(results),
        "record": dict(record),
        "per_opponent": {name: dict(counts) for name, counts in sorted(per_opponent.items())},
        "shop_pairs": {" | ".join(pair): count for pair, count in sorted(pairs.items())},
        "mean_final_margin": sum(item["final_margin"] for item in results) / len(results),
        "mean_hires": sum(item["hires"] for item in results) / len(results),
        "mean_route_efficiency": (sum(efficiencies) / len(efficiencies)) if (efficiencies := [
            item["route_health"]["mean_route_efficiency"] for item in results
            if item["route_health"].get("mean_route_efficiency") is not None]) else None,
        "mean_peak_hands": sum(item["mean_peak_hands"] for item in results) / len(results),
        "mean_disruption_excess": sum(item["disruption_excess"] for item in results) / len(results),
        "losses": [{
            "episode_id": item["episode_id"], "opponent": item["opponent"],
            "final_margin": item["final_margin"], "shop_pair": item["shop_pair"],
            "first_24_turn_deficit": item["first_24_turn_deficit"],
            "permanent_deficit_step": item["permanent_deficit_step"],
            "worst_day_erosion": item["worst_day_erosion"],
            "disruption_excess": item["disruption_excess"],
            "classification": ("more_disruption_than_opponent" if item["disruption_excess"] > 0
                               else "outplayed_while_routing_no_worse"),
        } for item in losses],
    }


def _from_snapshot(snapshot: str) -> tuple[list[tuple[Path, dict]], dict, dict]:
    snapshot_dir = ROOT / "experiments" / snapshot
    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    if manifest["status"] != "complete" or manifest.get("failures"):
        raise ValueError(f"snapshot {snapshot} is not a complete, failure-free capture")
    summary = json.loads((snapshot_dir / "summary.json").read_text())
    raw = {int(item["episode_id"]): item for item in manifest["raw_files"]}
    work = []
    for association in sorted(manifest["cohort"]["associations"], key=lambda item: item["episode_id"]):
        record = raw[int(association["episode_id"])]
        path = ROOT / record["path"]
        if digest(path) != record["sha256"]:
            raise ValueError(f"frozen evidence changed: {path}")
        work.append((path, association))
    team = manifest["cohort"]["teams"][0]
    return work, summary, {
        "snapshot_id": manifest["snapshot_id"],
        "captured_at": manifest["cohort"]["captured_at"],
        "team": {key: team[key] for key in ("rank", "team_id", "team_name",
                                            "leaderboard_score", "submission_id", "date_submitted")},
    }


def _from_directory(directory: str, team: str) -> tuple[list[tuple[Path, dict]], dict, dict]:
    """Same metrics over a loose replay cohort, so our own agent is comparable."""
    work = []
    for path in sorted((ROOT / directory).glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        names = replay["info"]["TeamNames"]
        if team not in names:
            raise ValueError(f"{path.name} does not contain team {team!r}")
        seat = names.index(team)
        work.append((path, {
            "episode_id": replay["info"]["EpisodeId"], "seat": seat,
            "opponent_submission_id": None,
        }))
    return work, {}, {"replay_dir": directory, "team": {"team_name": team}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot", help="frozen snapshot id under experiments/")
    source.add_argument("--replay-dir", help="loose replay directory, for example our own cohort")
    parser.add_argument("--team", help="team name to observe; required with --replay-dir")
    parser.add_argument("--output", default="experiments/leader-route-20260912")
    args = parser.parse_args(argv)
    if args.replay_dir and not args.team:
        parser.error("--replay-dir requires --team")

    if args.snapshot:
        work, summary, header = _from_snapshot(args.snapshot)
    else:
        work, summary, header = _from_directory(args.replay_dir, args.team)

    results, tapes = [], {}
    for path, association in work:
        item = analyze(path, association, summary)
        tapes[item["episode_id"]] = item.pop("_tape")
        results.append(item)
        print(json.dumps({key: item[key] for key in (
            "episode_id", "result", "final_margin", "opponent", "shop_pair",
            "hires", "mean_peak_hands", "disruption_excess")}), flush=True)

    determinism = tape_determinism(tapes)
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(json.dumps({
        **header, "summary": aggregate(results),
        "tape_determinism": determinism, "episodes": results,
    }, indent=2) + "\n")
    print(json.dumps({**aggregate(results), "tape_determinism": {
        key: determinism[key] for key in (
            "earliest_unit_divergence_step", "mean_unit_divergence_fraction")}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
