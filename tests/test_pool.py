"""Panel aggregation: a weak opponent must not veto a large gain."""
import unittest

from tools.run_pool import DEFAULT_WEIGHTS, panel_verdict, regression_floor


def panel(name, improvement, mean_margin=2500.0, games=48):
    return {'opponent': name, 'paired_improvement': improvement,
            'mean_margin': mean_margin, 'games': games}


class RegressionFloorTests(unittest.TestCase):
    def test_floor_is_never_tighter_than_the_absolute_minimum(self):
        self.assertEqual(regression_floor(0.0), -500.0)

    def test_floor_scales_with_the_size_of_the_panel_margin(self):
        self.assertEqual(regression_floor(40000.0), -2000.0)

    def test_floor_ignores_the_sign_of_the_margin(self):
        self.assertEqual(regression_floor(-40000.0), -2000.0)


class VerdictTests(unittest.TestCase):
    """The real case: +3,988 coins/game was dropped for a -79 against Astra."""

    def test_a_tiny_regression_no_longer_vetoes_a_large_gain(self):
        panels = [panel('champion', 3988.0), panel('public_state_router', 1500.0),
                  panel('astra', -79.0, mean_margin=17000.0)]
        verdict = panel_verdict(panels)
        self.assertTrue(verdict['accepted'], verdict)
        self.assertGreater(verdict['weighted_improvement'], 0)

    def test_a_catastrophic_regression_still_fails(self):
        panels = [panel('champion', 3988.0), panel('public_state_router', 1500.0),
                  panel('astra', -9000.0, mean_margin=17000.0)]
        verdict = panel_verdict(panels)
        self.assertFalse(verdict['accepted'])
        self.assertEqual(verdict['breached'], ['astra'])

    def test_a_negative_weighted_mean_fails_even_with_no_breach(self):
        panels = [panel('champion', -400.0), panel('public_state_router', -400.0),
                  panel('astra', -400.0, mean_margin=17000.0)]
        verdict = panel_verdict(panels)
        self.assertFalse(verdict['accepted'])
        self.assertLess(verdict['weighted_improvement'], 0)

    def test_foreign_opponents_outweigh_our_own_agents(self):
        self.assertGreater(DEFAULT_WEIGHTS['public_state_router'], DEFAULT_WEIGHTS['astra'])
        self.assertGreater(DEFAULT_WEIGHTS['champion'], DEFAULT_WEIGHTS['astra'])

    def test_weighting_follows_the_supplied_table(self):
        panels = [panel('champion', 1000.0), panel('astra', -1000.0)]
        heavy_champion = panel_verdict(panels, weights={'champion': 9.0, 'astra': 1.0})
        heavy_astra = panel_verdict(panels, weights={'champion': 1.0, 'astra': 9.0})
        self.assertGreater(heavy_champion['weighted_improvement'], 0)
        self.assertLess(heavy_astra['weighted_improvement'], 0)

    def test_an_unknown_opponent_gets_unit_weight_rather_than_being_dropped(self):
        verdict = panel_verdict([panel('champion', 100.0), panel('mystery', 100.0)])
        self.assertIn('mystery', verdict['weights'])
        self.assertEqual(verdict['weights']['mystery'], 1.0)

    def test_the_champion_panel_must_be_positive_on_its_own(self):
        panels = [panel('champion', -10.0), panel('public_state_router', 5000.0)]
        self.assertFalse(panel_verdict(panels)['accepted'])


if __name__ == '__main__':
    unittest.main()
