import unittest

from agents.shared.adaptive import TelemetryRecorder, adapt_action_dict


def observation(tile=None, action_hands=None):
    tiles = [[tile, None], [None, None]]
    return {
        "player": 0, "step": 12, "market": {"prices": {}}, "town": {"unlocked_shops": []},
        "farms": [{"farmer": [0, 0], "hands": action_hands or [], "tiles": tiles}],
        "private": {"inventories": [{}] + [{} for _ in (action_hands or [])], "seeds": {}},
    }


class AdaptiveTests(unittest.TestCase):
    def test_parity_when_guard_does_not_trigger(self):
        obs = observation()
        base = {"farmer": ["EAST"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}
        self.assertIs(adapt_action_dict(obs, base), base)

    def test_idle_weed_is_repaired_and_logged(self):
        obs = observation({"kind": "WEED"})
        recorder = TelemetryRecorder()
        result = adapt_action_dict(obs, {"farmer": ["PASS"], "hands": [], "market": []}, recorder)
        self.assertEqual(result["farmer"], ["DIG"])
        event = recorder.drain()[0]
        self.assertEqual(event["guard_reason"], "urgent_weed")
        self.assertEqual(event["unit"], 0)
        self.assertTrue(event["state_fingerprint"])

    def test_shape_is_preserved_for_valid_multi_unit_action(self):
        obs = observation(None, [[0, 0]])
        base = {"farmer": ["EAST"], "hands": [["SOUTH"]], "market": [["HIRE"]]}
        result = adapt_action_dict(obs, base)
        self.assertIs(result, base)
        self.assertEqual(len(result["hands"]), 1)
        self.assertEqual(len(result["market"]), 1)


if __name__ == "__main__":
    unittest.main()
