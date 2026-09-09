"""Conservative, submission-independent action repair for development variants."""

from __future__ import annotations

import hashlib
import json
from collections import Counter


MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
UNIT_OPS = MOVES | {
    "PASS", "PICKUP", "PLACE", "DROP", "PLANT", "WATER", "HARVEST",
    "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE", "FEED",
    "COLLECT_FERTILIZER", "CARE", "DIG",
}


class TelemetryRecorder:
    """In-memory events; callers decide whether and where to persist them."""

    def __init__(self):
        self.events = []
        self.counts = Counter()

    def emit(self, event):
        self.events.append(event)
        self.counts[event["type"]] += 1

    def drain(self):
        events, self.events = self.events, []
        return events


def _fingerprint(obs, unit, position):
    """Hash public state plus the player's own current tile; never opponent private state."""
    player = int(obs.get("player", 0))
    farm = obs["farms"][player]
    x, y = position
    tile = farm["tiles"][y][x] if 0 <= y < len(farm["tiles"]) and 0 <= x < len(farm["tiles"][y]) else None
    value = {
        "step": obs.get("step"), "unit": unit, "position": position, "tile": tile,
        "market": obs.get("market"), "town": obs.get("town"),
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _positions(obs):
    farm = obs["farms"][int(obs.get("player", 0))]
    return [tuple(farm["farmer"])] + [tuple(p) for p in farm.get("hands", [])]


def _invalid(action):
    if not isinstance(action, list) or not action or action[0] not in UNIT_OPS:
        return True
    op = action[0]
    if op in MOVES | {"PASS", "DROP", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE"}:
        return len(action) != 1
    if op == "PLANT":
        return len(action) != 2 or not isinstance(action[1], str)
    if op == "PICKUP":
        return len(action) not in (2, 3) or not isinstance(action[1], str)
    return len(action) not in (2, 3) or not isinstance(action[1], str)


def _certain_noop(action, tile, inv, seeds, pos, board):
    if _invalid(action):
        return True
    op = action[0]
    if op == "PASS":
        return True
    x, y = pos
    if op == "NORTH": return y == 0
    if op == "SOUTH": return y == board - 1
    if op == "WEST": return x == 0
    if op == "EAST": return x == board - 1
    is_dict = isinstance(tile, dict)
    kind = tile.get("kind") if is_dict else None
    animal = is_dict and tile.get("animal") is not None
    if op == "WATER": return kind != "PLANT" or bool(tile.get("watered_today"))
    if op == "FEED": return not animal or bool(tile.get("fed_today")) or inv.get("WHEAT", 0) <= 0
    if op == "DIG": return tile is None or animal
    if op == "PLANT": return tile is not None or seeds.get(action[1], 0) <= 0
    if op == "HARVEST": return not is_dict or tile.get("yield_units", 0) <= 0
    return False


def _emergency(tile, inv):
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        return ["DIG"], "urgent_weed"
    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today"):
        return ["WATER"], "urgent_water"
    if isinstance(tile, dict) and tile.get("animal") and not tile.get("fed_today") and inv.get("WHEAT", 0) > 0:
        return ["FEED"], "urgent_feed"
    return ["PASS"], "invalid_or_noop"


def adapt_action_dict(obs, base_action, recorder=None):
    """Return base action unchanged unless a unit action is certainly invalid/no-op."""
    positions = _positions(obs)
    if not isinstance(base_action, dict):
        base_action = {}
    actions = [base_action.get("farmer", ["PASS"])] + list(base_action.get("hands", []))
    # Structural repair is only for an already-invalid action dictionary.
    if len(actions) != len(positions):
        actions = actions[:len(positions)] + [["PASS"]] * max(0, len(positions) - len(actions))
    farm = obs["farms"][int(obs.get("player", 0))]
    inventories = obs.get("private", {}).get("inventories", [])
    seeds = obs.get("private", {}).get("seeds", {})
    board = len(farm["tiles"])
    changed = False
    for unit, (action, pos) in enumerate(zip(actions, positions)):
        x, y = pos
        tile = farm["tiles"][y][x] if 0 <= y < board and 0 <= x < len(farm["tiles"][y]) else None
        inv = inventories[unit] if unit < len(inventories) else {}
        if not _certain_noop(action, tile, inv, seeds, pos, board):
            continue
        replacement, reason = _emergency(tile, inv)
        if action == replacement:
            continue
        actions[unit] = replacement
        changed = True
        if recorder:
            recorder.emit({
                "type": "override", "turn": int(obs.get("step", 0)), "unit": unit,
                "base_action": action, "replacement": replacement, "guard_reason": reason,
                "state_fingerprint": _fingerprint(obs, unit, pos),
            })
    if not changed and isinstance(base_action, dict) and len(base_action.get("hands", [])) == len(positions) - 1:
        return base_action
    return {"farmer": actions[0], "hands": actions[1:], "market": list(base_action.get("market", []))}
