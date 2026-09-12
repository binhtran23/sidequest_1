"""Experimental shop_plan_probe entrypoint; not a promoted submission.

`SHOP_PLANS` has 15 keys and every one contains YARN_STORE, so most observed
openings fall through to plan 0. This probe forces the plan chosen at ROUTE_STEP
to a fixed index so each continuation can be scored on openings the table does
not cover.

Only the selection at step 144 is overridden. The forced switch to plan 2 at
FINAL_PLAN_STEP and every repair, sale and liquidation rule are untouched.
"""
import importlib.util
import json
import uuid
from pathlib import Path

_FOLDER = Path(__file__).resolve().parent
_ROUTER = _FOLDER.parents[1] / "base/router.py"
_SETTINGS = json.loads((_FOLDER / "settings.json").read_text())
_FORCE_PLAN = _SETTINGS.get("force_plan")


def _load(path):
    spec = importlib.util.spec_from_file_location("shop_plan_probe_" + uuid.uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load(_ROUTER)

# Root main.py is this router with one behavioural change applied by
# tools/build_route_submission.py: SALE_HORIZON 2 -> 3. Match it, or forcing the
# plan the champion would have picked anyway fails to reproduce the champion.
_MODULE.SALE_HORIZON = int(_SETTINGS.get("sale_horizon", 3))


class _ForcedPlans(dict):
    """Plan lookup that ignores the observed pair and returns one fixed plan."""

    def __init__(self, mapping, plan):
        super().__init__(mapping)
        self._plan = int(plan)

    def get(self, key, default=None):
        return self._plan


if _FORCE_PLAN is not None:
    if not 0 <= int(_FORCE_PLAN) < 13:
        raise ValueError("force_plan must index one of the 13 tapes")
    _MODULE.SHOP_PLANS = _ForcedPlans(_MODULE.SHOP_PLANS, _FORCE_PLAN)


def agent(observation, configuration=None):
    return _MODULE.agent(observation, configuration)
