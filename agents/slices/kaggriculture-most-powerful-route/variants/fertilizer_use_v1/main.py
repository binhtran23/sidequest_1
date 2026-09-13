"""Experimental fertilizer_use_v1 entrypoint; not a promoted submission.

Measured on 2026-09-12 over 12 local games and the frozen top-5 cohort
(`experiments/season-curves-20260912/`): the champion acquires more fertilizer
than any top-5 team, 343.8 units a game against their 287-332, and applies the
least of it, 67.7 FERTILIZE actions against their 113.7-199.0. The balance
leaves through the market: 108 SELL orders a game name FERTILIZER, and 304.5
units a game leave the shed that way.

The two settings separate the two halves of that. `fertilizer_reserve` keeps
stock off the market; `apply_on_pass` spends it, but only on a turn the
champion had already decided to idle, and only on the tile the unit is already
standing on. No route step moves, no hand is added or removed, and a unit that
was given real work keeps it.

This wraps root main.py rather than base/router.py on purpose. The router runs
at SALE_HORIZON 2 and the promoted champion at 3 -- a 3,630 coin/game packaging
difference that has already contaminated two experiments in this slice -- so
the control arm here is a provable no-op instead of an approximate one.
"""
import importlib.util
import json
import uuid
from pathlib import Path

_FOLDER = Path(__file__).resolve().parent
_ROOT = _FOLDER.parents[4]
_SETTINGS = json.loads((_FOLDER / "settings.json").read_text())

# Units of fertilizer to keep out of SELL orders; 0 leaves selling untouched.
_RESERVE = int(_SETTINGS.get("fertilizer_reserve", 0))
_APPLY = bool(_SETTINGS.get("apply_on_pass", False))
_PICKUP = int(_SETTINGS.get("pickup_units", 0))
_START_DAY = int(_SETTINGS.get("start_day", 0))
_END_DAY = int(_SETTINGS.get("end_day", 29))


def _load(path):
    spec = importlib.util.spec_from_file_location("fertilizer_use_" + uuid.uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load(_ROOT / "main.py")
LAST_STEP = 718
TURNS_PER_DAY = 24

# Withholding a sale withholds cash, and a HIRE the tape had budgeted for can
# then fail, leaving the tape emitting actions for a hand that was never hired.
# The engine rejects a mismatched hands list outright, so the count is forced
# back to the observation and `hand_desyncs` records how often that was needed.
# A non-zero count is a finding about the arm, not noise to be tidied away.
REPORT = {"fertilize": 0, "pickup": 0, "sales_dropped": 0, "sales_capped": 0,
          "hand_desyncs": 0, "hands_padded": 0, "hands_truncated": 0}


def _cap_sales(action, shed_fertilizer):
    """Keep `_RESERVE` units back; sell only what is above it."""
    orders = action.get("market")
    if not orders:
        return
    kept = []
    available = max(0, shed_fertilizer - _RESERVE)
    for order in orders:
        if order and order[0] == "SELL" and len(order) > 2 and order[1] == "FERTILIZER":
            try:
                quantity = int(order[2])
            except (TypeError, ValueError):
                kept.append(order)
                continue
            allowed = min(quantity, available)
            available -= allowed
            if allowed <= 0:
                REPORT["sales_dropped"] += 1
                continue  # Dropping the order frees a slot; it never adds one.
            if allowed < quantity:
                REPORT["sales_capped"] += 1
            order = [order[0], order[1], allowed, *order[3:]]
        kept.append(order)
    action["market"] = kept


def _apply(action, observation, day):
    """Spend held fertilizer on idle turns, on the unit's own tile only."""
    farm = observation["farms"][observation["player"]]
    private = observation["private"]
    tiles = farm["tiles"]
    positions = [farm["farmer"], *farm["hands"]]
    inventories = private.get("inventories") or []
    stock = max(0, int((private["shed"] or {}).get("FERTILIZER", 0) or 0))
    center = len(tiles) // 2

    commands = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    for unit in range(min(len(commands), len(positions))):
        if list(commands[unit]) != ["PASS"]:
            continue
        x, y = positions[unit]
        tile = tiles[y][x]
        carried = int((inventories[unit] if unit < len(inventories) else {} or {})
                      .get("FERTILIZER", 0) or 0)
        if (carried and isinstance(tile, dict) and tile.get("crop")
                and int(tile.get("fertilized_until_day", -1)) < day + 2):
            commands[unit] = ["FERTILIZE"]
            REPORT["fertilize"] += 1
        elif (_PICKUP and not carried and stock >= _PICKUP
              and x in (center - 1, center) and y in (center - 1, center)):
            commands[unit] = ["PICKUP", "FERTILIZER", _PICKUP]
            stock -= _PICKUP  # Two units must not both claim the same stock.
            REPORT["pickup"] += 1
    action["farmer"], action["hands"] = commands[0], commands[1:]


def _resize_hands(action, observation):
    hands = list(action.get("hands") or [])
    expected = len(observation["farms"][observation["player"]]["hands"])
    if len(hands) == expected:
        return
    REPORT["hand_desyncs"] += 1
    if len(hands) < expected:
        REPORT["hands_padded"] += expected - len(hands)
        hands += [["PASS"] for _ in range(expected - len(hands))]
    else:
        REPORT["hands_truncated"] += len(hands) - expected
        hands = hands[:expected]
    action["hands"] = hands


def agent(observation, configuration=None):
    action = _MODULE.agent(observation, configuration)
    step = int(observation["step"])
    day = step // TURNS_PER_DAY
    if step >= LAST_STEP or not _START_DAY <= day <= _END_DAY:
        return action
    if _RESERVE:
        _cap_sales(action, max(0, int((observation["private"]["shed"] or {})
                                      .get("FERTILIZER", 0) or 0)))
    if _APPLY:
        _apply(action, observation, day)
    if _RESERVE:
        _resize_hands(action, observation)
    return action


# benchmark.py reports a module's `_METRICS` as planner_metrics, and reloads the
# module per game, so these counts are per-game rather than cumulative.
_METRICS = REPORT
