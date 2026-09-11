"""Normalize Kaggriculture replay evidence into observer-only Parquet tables."""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from .routing import Waypoint, manhattan, optimise_route


class ReplayValidationError(ValueError):
    pass


MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
MOVE_DELTAS = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
NO_ARG_UNIT_OPS = {
    "PASS", "WATER", "HARVEST", "FERTILIZE", "BUILD_COOP",
    "BUILD_PASTURE", "DIG", "DROP", "FEED", "COLLECT_FERTILIZER", "CARE",
}
ITEM_UNIT_OPS = {"PICKUP", "PLACE", "PLANT"}
MARKET_OPS = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND"}
FIELD_TASKS = {
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "BUILD_COOP",
    "BUILD_PASTURE", "DIG", "DROP", "PLACE", "FEED", "COLLECT_FERTILIZER", "CARE",
}


EPISODE_SCHEMA = pa.schema([
    ("snapshot_id", pa.string()), ("association_id", pa.string()), ("episode_id", pa.int64()),
    ("rank", pa.int32()), ("team_id", pa.int64()), ("team_name", pa.string()),
    ("leaderboard_score", pa.string()), ("submission_id", pa.int64()), ("seat", pa.int8()),
    ("opponent_team_id", pa.int64()), ("opponent_team_name", pa.string()),
    ("opponent_submission_id", pa.int64()), ("seed", pa.int64()), ("result", pa.string()),
    ("reward", pa.float64()), ("opponent_reward", pa.float64()), ("step_count", pa.int32()),
    ("create_time", pa.string()), ("end_time", pa.string()), ("raw_path", pa.string()),
    ("raw_sha256", pa.string()), ("raw_byte_size", pa.int64()), ("downloaded_at", pa.string()),
])

TURN_SCHEMA = pa.schema([
    ("snapshot_id", pa.string()), ("association_id", pa.string()), ("episode_id", pa.int64()),
    ("team_id", pa.int64()), ("submission_id", pa.int64()), ("seat", pa.int8()),
    ("step", pa.int32()), ("day", pa.int16()), ("hour", pa.int16()),
    ("unit_id", pa.string()), ("unit_index", pa.int16()), ("position_x", pa.int16()),
    ("position_y", pa.int16()), ("next_position_x", pa.int16()), ("next_position_y", pa.int16()),
    ("action_op", pa.string()), ("action_args_json", pa.string()), ("action_json", pa.string()),
    ("market_actions_json", pa.string()), ("action_malformed", pa.bool_()),
    ("inferred_noop", pa.bool_()), ("moved", pa.bool_()), ("at_shed", pa.bool_()),
    ("inventory_json", pa.string()), ("inventory_delta_json", pa.string()),
    ("shed_json", pa.string()), ("seed_inventory_json", pa.string()),
    ("money", pa.float64()), ("money_delta", pa.float64()),
    ("assets_json", pa.string()), ("asset_delta_json", pa.string()),
    ("market_inventory_json", pa.string()), ("market_prices_json", pa.string()),
    ("town_shops_json", pa.string()), ("state_delta_json", pa.string()),
])

ROUTE_SCHEMA = pa.schema([
    ("snapshot_id", pa.string()), ("association_id", pa.string()), ("episode_id", pa.int64()),
    ("team_id", pa.int64()), ("seat", pa.int8()), ("day", pa.int16()),
    ("unit_id", pa.string()), ("chain_id", pa.string()), ("start_step", pa.int32()),
    ("end_step", pa.int32()), ("start_x", pa.int16()), ("start_y", pa.int16()),
    ("end_x", pa.int16()), ("end_y", pa.int16()), ("task_count", pa.int16()),
    ("segment_count", pa.int16()), ("shed_trip_count", pa.int16()),
    ("actual_movement", pa.int32()), ("shadow_movement", pa.int32()),
    ("movement_excess", pa.int32()), ("route_efficiency_ratio", pa.float64()),
    ("tasks_per_shed_trip", pa.float64()), ("idle_pass_rate", pa.float64()),
    ("inferred_noop_rate", pa.float64()), ("maintenance_slack", pa.int16()),
    ("batching_efficiency", pa.float64()), ("deadline_steps", pa.int16()),
    ("route_algorithm", pa.string()), ("route_feasible", pa.bool_()),
    ("actual_order_json", pa.string()), ("shadow_order_json", pa.string()),
    ("waypoints_json", pa.string()), ("boundary_events_json", pa.string()),
    ("route_score", pa.float64()),
])

STRATEGY_SCHEMA = pa.schema([
    ("snapshot_id", pa.string()), ("association_id", pa.string()), ("episode_id", pa.int64()),
    ("rank", pa.int32()), ("team_id", pa.int64()), ("seat", pa.int8()), ("day", pa.int16()),
    ("economic_phase", pa.string()), ("opening_money", pa.float64()), ("closing_money", pa.float64()),
    ("money_delta", pa.float64()), ("production_mix_json", pa.string()),
    ("opening_assets_json", pa.string()), ("closing_assets_json", pa.string()),
    ("asset_trajectory_json", pa.string()), ("hires", pa.int16()), ("land_purchases", pa.int16()),
    ("sale_orders", pa.int16()), ("units_offered_for_sale", pa.int32()),
    ("maintenance_actions", pa.int32()), ("field_tasks", pa.int32()),
    ("shed_trips", pa.int32()), ("mean_route_efficiency", pa.float64()),
])


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _numeric_map(value: Any) -> dict[str, int | float]:
    return {str(k): v for k, v in _dict(value).items() if isinstance(v, (int, float))}


def _delta(after: dict, before: dict) -> dict:
    result = {}
    for key in sorted(set(before) | set(after)):
        change = after.get(key, 0) - before.get(key, 0)
        if change:
            result[key] = change
    return result


def _asset_counts(farm: dict) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in farm.get("tiles", []) if isinstance(farm, dict) else []:
        for tile in row if isinstance(row, list) else []:
            if not isinstance(tile, dict):
                continue
            label = tile.get("crop") or tile.get("animal") or tile.get("kind")
            if label:
                counts[str(label)] += 1
    return dict(sorted(counts.items()))


def _position(farm: dict, unit_index: int) -> tuple[int | None, int | None]:
    if unit_index == 0:
        raw = farm.get("farmer")
    else:
        hands = farm.get("hands") or []
        raw = hands[unit_index - 1] if unit_index - 1 < len(hands) else None
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return int(raw[0]), int(raw[1])
    return None, None


def _unit_inventory(private: dict, unit_index: int) -> dict:
    inventories = private.get("inventories", []) if isinstance(private, dict) else []
    if unit_index < len(inventories):
        return _numeric_map(inventories[unit_index])
    return {}


def _at_shed(position: tuple[int | None, int | None], board_size: int) -> bool:
    if None in position:
        return False
    half = board_size // 2
    return position in {(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)}


def _end_of_day_position(op: str, position, farm: dict, board_size: int):
    """Remove the engine's automatic end-of-day teleport from route movement."""
    if op not in MOVE_DELTAS or None in position:
        return position
    dx, dy = MOVE_DELTAS[op]
    target = (position[0] + dx, position[1] + dy)
    if not (0 <= target[0] < board_size and 0 <= target[1] < board_size):
        return position
    tiles = farm.get("tiles", [])
    if target[1] >= len(tiles) or target[0] >= len(tiles[target[1]]) or tiles[target[1]][target[0]] == "LOCKED":
        return position
    return target


def _unwrap_replay(payload: Any) -> dict:
    current = payload
    for _ in range(4):
        if isinstance(current, str):
            current = json.loads(current)
            continue
        if isinstance(current, dict) and "steps" in current:
            return current
        if isinstance(current, dict):
            for key in ("replay", "result", "episode"):
                if key in current:
                    current = current[key]
                    break
            else:
                break
    raise ReplayValidationError("payload does not contain a Kaggle replay")


def load_replay(path: Path, *, require_complete: bool = True) -> dict:
    try:
        replay = _unwrap_replay(json.loads(path.read_text()))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ReplayValidationError(f"cannot parse replay {path}: {exc}") from exc
    steps = replay.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ReplayValidationError(f"replay {path} has no steps")
    expected = int(_dict(replay.get("configuration")).get("episodeSteps", 720))
    if require_complete and len(steps) != expected:
        raise ReplayValidationError(
            f"incomplete replay {path}: {len(steps)} steps, expected {expected}"
        )
    for index, step in enumerate(steps):
        if not isinstance(step, list) or len(step) != 2:
            raise ReplayValidationError(f"replay {path} step {index} is not a two-player state")
    return replay


def _valid_action(action: Any) -> tuple[str, list, bool]:
    if not isinstance(action, list) or not action or not isinstance(action[0], str):
        return "INVALID", [], True
    op, args = action[0], action[1:]
    malformed = (
        (op in MOVES | NO_ARG_UNIT_OPS and bool(args))
        or (op in ITEM_UNIT_OPS and not args)
        or op not in MOVES | NO_ARG_UNIT_OPS | ITEM_UNIT_OPS
    )
    return op, args, malformed


def _action_at(action_dict: Any, unit_index: int) -> tuple[Any, bool]:
    if not isinstance(action_dict, dict):
        return None, True
    if unit_index == 0:
        return action_dict.get("farmer"), "farmer" not in action_dict
    hands = action_dict.get("hands")
    if not isinstance(hands, list) or unit_index - 1 >= len(hands):
        return None, True
    return hands[unit_index - 1], False


def _local_signature(farm: dict, private: dict, unit_index: int, position) -> str:
    tile = None
    if None not in position:
        tiles = farm.get("tiles", [])
        x, y = position
        if 0 <= y < len(tiles) and isinstance(tiles[y], list) and 0 <= x < len(tiles[y]):
            tile = tiles[y][x]
    return _json({
        "position": position, "tile": tile, "private": private,
        "money": farm.get("money"), "hands": farm.get("hands"),
        "unlocked": farm.get("unlocked_quadrants"), "unit": unit_index,
    })


def _turn_rows(replay: dict, association: dict, snapshot_id: str) -> list[dict]:
    seat = int(association["seat"])
    configuration = _dict(replay.get("configuration"))
    board_size = int(configuration.get("boardSize", 10))
    turns_per_day = int(configuration.get("turnsPerDay", 24))
    result = []
    steps = replay["steps"]
    for step_index, pair in enumerate(steps):
        current = _dict(pair[seat])
        previous = _dict(steps[step_index - 1][seat]) if step_index else current
        # Kaggle records the action on the state it produced. Attribute the
        # transition to current.action by comparing the prior observation with
        # the current (post-action) observation.
        obs, next_obs = _dict(previous.get("observation")), _dict(current.get("observation"))
        if "player" in obs and int(obs["player"]) != seat:
            raise ReplayValidationError(
                f"episode {association['episode_id']} step {step_index}: private-state seat mismatch"
            )
        farms, next_farms = obs.get("farms", []), next_obs.get("farms", [])
        if seat >= len(farms) or seat >= len(next_farms):
            raise ReplayValidationError(
                f"episode {association['episode_id']} step {step_index}: missing public farm"
            )
        farm, next_farm = _dict(farms[seat]), _dict(next_farms[seat])
        private, next_private = _dict(obs.get("private")), _dict(next_obs.get("private"))
        hands = farm.get("hands", []) if isinstance(farm.get("hands", []), list) else []
        action_dict = current.get("action")
        market_actions = action_dict.get("market", []) if isinstance(action_dict, dict) else []
        assets, next_assets = _asset_counts(farm), _asset_counts(next_farm)
        market = _dict(obs.get("market"))
        day = int(obs.get("day", step_index // turns_per_day))
        hour = int(obs.get("hour", step_index % turns_per_day))
        for unit_index in range(1 + len(hands)):
            action, missing = _action_at(action_dict, unit_index)
            op, args, malformed = _valid_action(action)
            malformed = malformed or missing
            pos, next_pos = _position(farm, unit_index), _position(next_farm, unit_index)
            if int(next_obs.get("day", day)) != day:
                next_pos = _end_of_day_position(op, pos, farm, board_size)
            inventory = _unit_inventory(private, unit_index)
            next_inventory = _unit_inventory(next_private, unit_index)
            before_sig = _local_signature(farm, private, unit_index, pos)
            after_sig = _local_signature(next_farm, next_private, unit_index, next_pos)
            inferred_noop = malformed or (op != "PASS" and before_sig == after_sig)
            money = float(farm.get("money", 0.0))
            next_money = float(next_farm.get("money", money))
            state_delta = {
                "inventory": _delta(next_inventory, inventory),
                "shed": _delta(_numeric_map(next_private.get("shed")), _numeric_map(private.get("shed"))),
                "seeds": _delta(_numeric_map(next_private.get("seeds")), _numeric_map(private.get("seeds"))),
                "assets": _delta(next_assets, assets),
                "money": next_money - money,
            }
            result.append({
                "snapshot_id": snapshot_id, "association_id": association["association_id"],
                "episode_id": int(association["episode_id"]), "team_id": int(association["team_id"]),
                "submission_id": int(association["submission_id"]), "seat": seat,
                "step": step_index, "day": day, "hour": hour,
                "unit_id": "farmer" if unit_index == 0 else f"hand-{unit_index - 1}",
                "unit_index": unit_index, "position_x": pos[0], "position_y": pos[1],
                "next_position_x": next_pos[0], "next_position_y": next_pos[1],
                "action_op": op, "action_args_json": _json(args), "action_json": _json(action),
                "market_actions_json": _json(market_actions), "action_malformed": malformed,
                "inferred_noop": inferred_noop,
                "moved": None not in pos + next_pos and pos != next_pos,
                "at_shed": _at_shed(pos, board_size), "inventory_json": _json(inventory),
                "inventory_delta_json": _json(_delta(next_inventory, inventory)),
                "shed_json": _json(_numeric_map(private.get("shed"))),
                "seed_inventory_json": _json(_numeric_map(private.get("seeds"))),
                "money": money, "money_delta": next_money - money, "assets_json": _json(assets),
                "asset_delta_json": _json(_delta(next_assets, assets)),
                "market_inventory_json": _json(_numeric_map(market.get("inventory"))),
                "market_prices_json": _json(_numeric_map(market.get("prices"))),
                "town_shops_json": _json(_dict(obs.get("town")).get("unlocked_shops", [])),
                "state_delta_json": _json(state_delta),
            })
    return result


def _intent(op: str) -> str:
    return {
        "PICKUP": "acquire_supplies", "PLANT": "plant", "WATER": "maintain",
        "FERTILIZE": "maintain", "FEED": "maintain", "CARE": "maintain",
        "HARVEST": "harvest", "COLLECT_FERTILIZER": "collect", "PLACE": "deliver",
        "DROP": "deliver",
        "BUILD_COOP": "build", "BUILD_PASTURE": "build", "DIG": "maintain",
    }.get(op, "task")


def _waypoints(chain: list[dict]) -> tuple[list[Waypoint], list[dict]]:
    values = []
    events = []
    if chain[0]["hour"] == 0:
        events.append({"step": chain[0]["step"], "type": "day_boundary"})
    prior_inventory = None
    prior_at_shed = False
    for index, row in enumerate(chain):
        if row["at_shed"] and (index == 0 or not prior_at_shed):
            events.append({"step": row["step"], "type": "shed_visit"})
        prior_at_shed = row["at_shed"]
        inventory = row["inventory_json"]
        if prior_inventory is not None and inventory != prior_inventory:
            events.append({"step": row["step"], "type": "inventory_transition"})
        prior_inventory = inventory
        if row["action_op"] not in FIELD_TASKS | {"PICKUP"} or row["inferred_noop"]:
            continue
        if row["position_x"] is None or row["position_y"] is None:
            continue
        waypoint_id = f"w{len(values):03d}"
        values.append(Waypoint(waypoint_id, row["position_x"], row["position_y"], _intent(row["action_op"])))
        events.append({"step": row["step"], "type": "completed_task", "waypoint_id": waypoint_id})

    # Preserve supply and same-tile task precedence observed in the replay.
    precedes: dict[str, set[str]] = {item.waypoint_id: set() for item in values}
    source_rows = [
        row for row in chain
        if row["action_op"] in FIELD_TASKS | {"PICKUP"}
        and not row["inferred_noop"]
        and row["position_x"] is not None and row["position_y"] is not None
    ]
    last_pickup: dict[str, str] = {}
    last_by_tile: dict[tuple[int, int, str], str] = {}
    for waypoint, row in zip(values, source_rows):
        args = json.loads(row["action_args_json"])
        op = row["action_op"]
        item = str(args[0]) if args else ("WHEAT" if op == "FEED" else "")
        if op == "PICKUP" and item:
            last_pickup[item] = waypoint.waypoint_id
        if op in {"PLACE", "FEED"} and item in last_pickup:
            precedes[last_pickup[item]].add(waypoint.waypoint_id)
        tile = (row["position_x"], row["position_y"])
        for prior_op in {
            "PLACE": ("BUILD_COOP", "BUILD_PASTURE"),
            "WATER": ("PLANT",), "FERTILIZE": ("PLANT",),
            "HARVEST": ("PLANT", "WATER", "FERTILIZE"),
        }.get(op, ()):
            prior = last_by_tile.get((*tile, prior_op))
            if prior:
                precedes[prior].add(waypoint.waypoint_id)
        last_by_tile[(*tile, op)] = waypoint.waypoint_id
    values = [
        Waypoint(item.waypoint_id, item.x, item.y, item.intent, tuple(sorted(precedes[item.waypoint_id])))
        for item in values
    ]
    return values, events


def _route_row(chain: list[dict], chain_number: int, turns_per_day: int) -> dict:
    first, last = chain[0], chain[-1]
    start = (first["position_x"], first["position_y"])
    end = (last["next_position_x"], last["next_position_y"])
    if None in end:
        end = (last["position_x"], last["position_y"])
    waypoints, boundary_events = _waypoints(chain)
    deadline = max(0, turns_per_day - int(first["hour"]) - len(waypoints))
    solution = optimise_route(start, end, waypoints, deadline_steps=deadline)
    actual = sum(manhattan(
        (row["position_x"], row["position_y"]),
        (row["next_position_x"], row["next_position_y"]),
    ) for row in chain if None not in (
        row["position_x"], row["position_y"], row["next_position_x"], row["next_position_y"]
    ))
    shadow = solution.distance
    efficiency = 1.0 if actual == shadow == 0 else (shadow / actual if actual else 0.0)
    shed_transitions = sum(
        row["at_shed"] and (index == 0 or not chain[index - 1]["at_shed"])
        for index, row in enumerate(chain)
    )
    task_count = len(waypoints)
    maintenance_slacks = [
        turns_per_day - 1 - int(row["hour"])
        for row in chain if row["action_op"] in {"WATER", "FEED", "CARE"} and not row["inferred_noop"]
    ]
    actual_order = [item.waypoint_id for item in waypoints]
    waypoint_payload = [
        {"waypoint_id": item.waypoint_id, "x": item.x, "y": item.y,
         "intent": item.intent, "precedes": list(item.precedes)} for item in waypoints
    ]
    return {
        "snapshot_id": first["snapshot_id"], "association_id": first["association_id"],
        "episode_id": first["episode_id"], "team_id": first["team_id"], "seat": first["seat"],
        "day": first["day"], "unit_id": first["unit_id"],
        "chain_id": f"{first['association_id']}:{first['day']}:{first['unit_id']}:{chain_number}",
        "start_step": first["step"], "end_step": last["step"],
        "start_x": start[0], "start_y": start[1], "end_x": end[0], "end_y": end[1],
        "task_count": task_count, "segment_count": max(1, len(boundary_events) + 1),
        "shed_trip_count": shed_transitions, "actual_movement": actual,
        "shadow_movement": shadow, "movement_excess": max(0, actual - shadow),
        "route_efficiency_ratio": efficiency,
        "tasks_per_shed_trip": task_count / max(1, shed_transitions),
        "idle_pass_rate": sum(row["action_op"] == "PASS" for row in chain) / len(chain),
        "inferred_noop_rate": sum(row["inferred_noop"] is True for row in chain) / len(chain),
        "maintenance_slack": min(maintenance_slacks) if maintenance_slacks else None,
        "batching_efficiency": task_count / max(1, task_count + shed_transitions),
        "deadline_steps": deadline, "route_algorithm": solution.algorithm,
        "route_feasible": solution.feasible, "actual_order_json": _json(actual_order),
        "shadow_order_json": _json(solution.order), "waypoints_json": _json(waypoint_payload),
        "boundary_events_json": _json(boundary_events), "route_score": efficiency,
    }


def _route_rows(turns: list[dict], turns_per_day: int) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in turns:
        grouped[(row["association_id"], row["day"], row["unit_id"])].append(row)
    result = []
    for key in sorted(grouped):
        rows = sorted(grouped[key], key=lambda row: row["step"])
        chains, current, has_left_shed = [], [], False
        for row in rows:
            current.append(row)
            has_left_shed = has_left_shed or not row["at_shed"]
            if row["at_shed"] and has_left_shed and len(current) > 1:
                chains.append(current)
                current, has_left_shed = [], False
        if current:
            chains.append(current)
        for number, chain in enumerate(chains):
            result.append(_route_row(chain, number, turns_per_day))
    return result


def _market_counts(rows: list[dict]) -> Counter:
    counts = Counter()
    # Market actions repeat for each unit, so count once per step from the farmer.
    for row in rows:
        if row["unit_index"] != 0:
            continue
        for action in json.loads(row["market_actions_json"]):
            if not isinstance(action, list) or not action:
                counts["MALFORMED"] += 1
                continue
            op = action[0]
            counts[op] += 1
            if op == "SELL" and len(action) >= 3 and isinstance(action[2], (int, float)):
                counts["SELL_UNITS"] += int(action[2])
    return counts


def _economic_phase(day: int, counts: Counter, assets_delta: dict) -> str:
    if day >= 27 or counts["SELL"] > counts["BUY_SEED"] + counts["BUY_ANIMAL"]:
        return "liquidation"
    if counts["BUY_LAND"] or counts["HIRE"] or counts["BUY_ANIMAL"]:
        return "buildout"
    if day <= 3 and sum(max(0, value) for value in assets_delta.values()) > 0:
        return "opening"
    return "production"


def _strategy_rows(
    turns: list[dict], routes: list[dict], association: dict, snapshot_id: str
) -> list[dict]:
    farmer_by_day: dict[int, list[dict]] = defaultdict(list)
    for row in turns:
        if row["unit_index"] == 0:
            farmer_by_day[row["day"]].append(row)
    routes_by_day: dict[int, list[dict]] = defaultdict(list)
    for row in routes:
        routes_by_day[row["day"]].append(row)
    result = []
    all_turns_by_day: dict[int, list[dict]] = defaultdict(list)
    for row in turns:
        all_turns_by_day[row["day"]].append(row)
    for day in sorted(farmer_by_day):
        farmer = sorted(farmer_by_day[day], key=lambda row: row["step"])
        day_turns = all_turns_by_day[day]
        opening_assets = json.loads(farmer[0]["assets_json"])
        closing_assets = json.loads(farmer[-1]["assets_json"])
        for key, change in json.loads(farmer[-1]["asset_delta_json"]).items():
            closing_assets[key] = closing_assets.get(key, 0) + change
            if closing_assets[key] == 0:
                del closing_assets[key]
        asset_change = _delta(closing_assets, opening_assets)
        market = _market_counts(day_turns)
        day_routes = routes_by_day[day]
        production = {k: v for k, v in closing_assets.items() if k not in {"WEED", "COOP", "PASTURE"}}
        efficiencies = [row["route_efficiency_ratio"] for row in day_routes if row["task_count"]]
        trajectory = [
            {"step": row["step"], "assets": json.loads(row["assets_json"]), "money": row["money"]}
            for row in farmer if row["hour"] in {0, 6, 12, 18, 23}
        ]
        result.append({
            "snapshot_id": snapshot_id, "association_id": association["association_id"],
            "episode_id": int(association["episode_id"]), "rank": int(association["rank"]),
            "team_id": int(association["team_id"]), "seat": int(association["seat"]), "day": day,
            "economic_phase": _economic_phase(day, market, asset_change),
            "opening_money": farmer[0]["money"],
            "closing_money": farmer[-1]["money"] + farmer[-1]["money_delta"],
            "money_delta": farmer[-1]["money"] + farmer[-1]["money_delta"] - farmer[0]["money"],
            "production_mix_json": _json(production), "opening_assets_json": _json(opening_assets),
            "closing_assets_json": _json(closing_assets), "asset_trajectory_json": _json(trajectory),
            "hires": market["HIRE"], "land_purchases": market["BUY_LAND"],
            "sale_orders": market["SELL"], "units_offered_for_sale": market["SELL_UNITS"],
            "maintenance_actions": sum(
                row["action_op"] in {"WATER", "FEED", "CARE", "FERTILIZE", "DIG"}
                and not row["inferred_noop"] for row in day_turns
            ),
            "field_tasks": sum(row["action_op"] in FIELD_TASKS and not row["inferred_noop"] for row in day_turns),
            "shed_trips": sum(row["shed_trip_count"] for row in day_routes),
            "mean_route_efficiency": sum(efficiencies) / len(efficiencies) if efficiencies else None,
        })
    return result


def _episode_row(replay: dict, association: dict, raw: dict, snapshot_id: str) -> dict:
    seat = int(association["seat"])
    final_pair = replay["steps"][-1]
    reward = final_pair[seat].get("reward")
    opponent_reward = final_pair[1 - seat].get("reward")
    if reward is None:
        agent = next((item for item in association.get("agents", []) if item["seat"] == seat), {})
        reward = agent.get("reward")
    if opponent_reward is None:
        agent = next((item for item in association.get("agents", []) if item["seat"] != seat), {})
        opponent_reward = agent.get("reward")
    result = "unknown"
    if reward is not None and opponent_reward is not None:
        result = "win" if reward > opponent_reward else "loss" if reward < opponent_reward else "draw"
    seed = _dict(replay.get("info")).get("seed")
    if seed is None:
        seed = _dict(replay.get("configuration")).get("seed")
    return {
        "snapshot_id": snapshot_id, "association_id": association["association_id"],
        "episode_id": int(association["episode_id"]), "rank": int(association["rank"]),
        "team_id": int(association["team_id"]), "team_name": association["team_name"],
        "leaderboard_score": association["leaderboard_score"],
        "submission_id": int(association["submission_id"]), "seat": seat,
        "opponent_team_id": association.get("opponent_team_id"),
        "opponent_team_name": association.get("opponent_team_name"),
        "opponent_submission_id": association.get("opponent_submission_id"),
        "seed": int(seed) if seed is not None else None, "result": result,
        "reward": float(reward) if reward is not None else None,
        "opponent_reward": float(opponent_reward) if opponent_reward is not None else None,
        "step_count": len(replay["steps"]), "create_time": association.get("create_time"),
        "end_time": association.get("end_time"), "raw_path": raw["path"],
        "raw_sha256": raw["sha256"], "raw_byte_size": int(raw["byte_size"]),
        "downloaded_at": raw.get("downloaded_at"),
    }


def _write_parquet(path: Path, rows: Iterable[dict], schema: pa.Schema) -> int:
    rows = list(rows)
    table = pa.Table.from_pylist(rows, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    pq.write_table(table, temporary, compression="zstd", use_dictionary=True)
    os.replace(temporary, path)
    return table.num_rows


def normalize_snapshot(manifest: dict, root: Path, raw_output: Path) -> tuple[dict, dict[str, list[dict]]]:
    """Normalize every frozen association and atomically replace derived tables."""
    snapshot_id = manifest["snapshot_id"]
    raw_by_episode = {int(item["episode_id"]): item for item in manifest["raw_files"]}
    episodes: list[dict] = []
    turns: list[dict] = []
    routes: list[dict] = []
    strategies: list[dict] = []
    grouped: dict[int, list[dict]] = defaultdict(list)
    for association in manifest["cohort"]["associations"]:
        grouped[int(association["episode_id"])].append(association)
    for episode_id in sorted(grouped):
        raw = raw_by_episode[episode_id]
        replay = load_replay(root / raw["path"])
        turns_per_day = int(_dict(replay.get("configuration")).get("turnsPerDay", 24))
        for association in sorted(grouped[episode_id], key=lambda item: item["association_id"]):
            association_turns = _turn_rows(replay, association, snapshot_id)
            association_routes = _route_rows(association_turns, turns_per_day)
            episodes.append(_episode_row(replay, association, raw, snapshot_id))
            turns.extend(association_turns)
            routes.extend(association_routes)
            strategies.extend(_strategy_rows(association_turns, association_routes, association, snapshot_id))
    datasets = {
        "episodes.parquet": (episodes, EPISODE_SCHEMA),
        "turns.parquet": (turns, TURN_SCHEMA),
        "routes.parquet": (routes, ROUTE_SCHEMA),
        "strategy_days.parquet": (strategies, STRATEGY_SCHEMA),
    }
    counts = {name: _write_parquet(raw_output / name, rows, schema) for name, (rows, schema) in datasets.items()}
    return counts, {"episodes": episodes, "turns": turns, "routes": routes, "strategy_days": strategies}


def validate_referential_integrity(tables: dict[str, list[dict]], manifest: dict) -> None:
    associations = {item["association_id"] for item in manifest["cohort"]["associations"]}
    episode_ids = {row["association_id"] for row in tables["episodes"]}
    if episode_ids != associations:
        raise ReplayValidationError("episodes table does not contain exactly the frozen associations")
    for name in ("turns", "routes", "strategy_days"):
        unknown = {row["association_id"] for row in tables[name]} - episode_ids
        if unknown:
            raise ReplayValidationError(f"{name} contains unknown associations: {sorted(unknown)}")
    turn_keys = [(row["association_id"], row["step"], row["unit_id"]) for row in tables["turns"]]
    if len(turn_keys) != len(set(turn_keys)):
        raise ReplayValidationError("turns table contains duplicate association/step/unit rows")
    strategy_keys = [(row["association_id"], row["day"]) for row in tables["strategy_days"]]
    if len(strategy_keys) != len(set(strategy_keys)):
        raise ReplayValidationError("strategy_days contains duplicate association/day rows")
