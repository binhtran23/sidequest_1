"""Experimental sale_granularity_v1 entrypoint; not a promoted submission.

Sale prices are dynamic with shared market inventory (COMPETITION_RULES.md), so
a single large SELL floods the pool and clears at a depressed price. The rank-1
agent observed on 2026-09-12 never exceeds roughly 17 units in a step (median 1
to 8); our champion's standing orders reach 1000 on seven of nine products.

This variant changes only the size of SELL orders the champion already decided
to place. It never adds, removes or retimes a sale, never touches a purchase,
hire or unit action, and leaves the final-turn liquidation uncapped.
"""
import importlib.util
import json
import uuid
from pathlib import Path

_FOLDER = Path(__file__).resolve().parent
_SLICE = _FOLDER.parents[1]
_ROUTER = _SLICE / "base/router.py"
_SETTINGS = json.loads((_FOLDER / "settings.json").read_text())

_MAX_SELL_UNITS = int(_SETTINGS.get("max_sell_units", 0))
# Capping a sale keeps stock in a shed that discards overflow past 100 items at
# end of day, so the cap lifts once the shed is under real pressure.
_SHED_PRESSURE = int(_SETTINGS.get("shed_pressure", 0))


def _load(path):
    spec = importlib.util.spec_from_file_location("sale_granularity_" + uuid.uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load(_ROUTER)

# Root main.py is this router with SALE_HORIZON 2 -> 3 applied by
# tools/build_route_submission.py. Match it, or the measured effect is that
# packaging difference rather than the cap under test.
_MODULE.SALE_HORIZON = int(_SETTINGS.get("sale_horizon", 3))


def _shed_total(observation):
    shed = observation["private"]["shed"]
    return sum(max(0, int(quantity)) for quantity in shed.values())


def agent(observation, configuration=None):
    action = _MODULE.agent(observation, configuration)
    step = int(observation["step"])
    if not _MAX_SELL_UNITS or step >= _MODULE.LAST_STEP:
        return action
    if _SHED_PRESSURE and _shed_total(observation) >= _SHED_PRESSURE:
        return action
    orders = action.get("market")
    if not orders:
        return action
    capped = []
    for order in orders:
        if order and order[0] == "SELL" and len(order) > 2:
            try:
                quantity = int(order[2])
            except (TypeError, ValueError):
                capped.append(order)
                continue
            if quantity > _MAX_SELL_UNITS:
                order = [order[0], order[1], _MAX_SELL_UNITS, *order[3:]]
        capped.append(order)
    action["market"] = capped
    return action
