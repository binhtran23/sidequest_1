import copy
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

PATH = Path(__file__).resolve().parents[1] / "agents/slices/kaggriculture-most-powerful-route/variants/test_v1/policy.py"
SPEC = importlib.util.spec_from_file_location("route_test", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def observation(step=309):
    farm = {"tiles": [[None]*10 for _ in range(10)], "farmer": [4,4], "hands": [],
            "money": 5000, "hires_today": 0, "unlocked_quadrants": ["NW", "NE", "SW"]}
    return {"step": step, "player": 0, "day": step//24, "hour": step%24,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"shed": {"MILK": 6, "WHEAT": 0}, "seeds": {}, "inventories": [{}]},
            "market": {"inventory": {p:10000 for p in MODULE.load(MODULE.ASTRA).PARAMS},
                       "prices": {"MILK":160, "WHEAT":25, "CARROT":35}},
            "town": {"unlocked_shops": []}}


def blank():
    return {"farmer": ["PASS"], "hands": [], "market": []}


class RouteExperimentTests(unittest.TestCase):
    def setUp(self):
        self.policy = MODULE.TestPolicy({"sale_pressure": True})
        self.obs = observation()
        self.obs["farms"][1]["tiles"][4][4] = {"kind":"PASTURE", "animal":"COW", "yield_units":6}
        self.policy.context = self.obs, {}
        self.state = SimpleNamespace(queues={}, sale_window_debts={}, sale_due_step=-1, advanced_sales={})
        self.tape = [blank() for _ in range(719)]
        self.tape[313]["market"] = [["SELL", "MILK", 6]]

    def test_early_sale_is_subtracted_once_from_future_order(self):
        action = blank()
        self.policy.reserve_sales(action, self.policy.router.FarmView(self.obs), self.state, self.tape, 309)
        self.assertEqual(action["market"], [["SELL", "MILK", 6]])
        due = copy.deepcopy(self.tape[313])
        self.policy.router.subtract_advanced_sales(due, self.state, 313)
        self.assertEqual(due["market"], [["SELL", "MILK", 0]])
        self.assertEqual(self.state.sale_window_debts, {})

    def test_upcoming_pickup_protects_inventory(self):
        self.tape[312]["farmer"] = ["PICKUP", "MILK", 6]
        action = blank()
        self.policy.reserve_sales(action, self.policy.router.FarmView(self.obs), self.state, self.tape, 309)
        self.assertEqual(action["market"], [])

    def test_town_demand_can_favor_waiting(self):
        self.obs["town"]["unlocked_shops"] = ["SMOOTHIE_SHOP"]*8
        action = blank()
        self.policy.reserve_sales(action, self.policy.router.FarmView(self.obs), self.state, self.tape, 309)
        self.assertEqual(action["market"], [])

    def test_feed_buy_accounts_for_existing_purchase(self):
        self.obs["step"] = 170
        self.obs["day"], self.obs["hour"] = 7, 2
        self.tape[171]["farmer"] = ["PICKUP", "WHEAT", 2]
        self.policy.router._POLICY = SimpleNamespace(players={0:SimpleNamespace(plan=0,queues={})}, tapes=[self.tape])
        action = blank()
        self.policy.feed_supply(self.obs, action)
        self.assertEqual(action["market"], [["BUY_PRODUCT", "WHEAT", 2]])
        action = blank()
        action["market"] = [["BUY_PRODUCT", "WHEAT", 2]]
        self.policy.feed_supply(self.obs, action)
        self.assertEqual(action["market"], [["BUY_PRODUCT", "WHEAT", 2]])

    def test_feed_allows_empty_native_market_slots(self):
        self.obs["step"] = 170
        self.tape[171]["farmer"] = ["PICKUP", "WHEAT", 2]
        self.policy.router._POLICY = SimpleNamespace(players={0:SimpleNamespace(plan=0,queues={})}, tapes=[self.tape])
        action = blank()
        action["market"] = [[]]
        self.policy.feed_supply(self.obs, action)
        self.assertEqual(action["market"], [[], ["BUY_PRODUCT", "WHEAT", 2]])

    def test_final_route_delivers_harvest_before_deadline(self):
        from kaggle_environments.envs.kaggriculture import kaggriculture as engine
        obs = observation(698)
        obs["private"]["shed"] = {}
        obs["farms"][0]["tiles"][3][4] = {
            "kind":"PLANT", "crop":"CARROT", "planted_day":26, "yield_units":4,
            "watered_today":True, "fertilized_until_day":-1,
        }
        state = {}
        for step in range(698, 719):
            obs["step"] = step
            self.policy.context = obs, {}
            action = blank()
            self.policy.endgame(obs, action, state)
            engine._apply_unit_action(obs["farms"][0], obs["private"], 0, action["farmer"], 10, 29, 24)
            for order in action["market"]:
                for _ in range(order[2]):
                    engine._commit_unit("SELL", order[1], obs["market"]["prices"][order[1]],
                                        obs["farms"][0], obs["private"], obs["market"])
        self.assertEqual(obs["farms"][0]["money"], 5140)
        self.assertEqual(sum(obs["private"]["inventories"][0].values()), 0)


if __name__ == "__main__":
    unittest.main()
