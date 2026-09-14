"""Phase 3b: advance sales of goods whose price is already sliding.

The engine prices every unit off live market inventory
(`kaggriculture.py:590-628`) and the only demand is the town's few units a day
(`_town_consume`), so a good in glut never recovers -- in a measured game WOOL
runs 217 -> 154 -> 1 between days 6 and 18 and never comes back. For such a
good a later sale is strictly a worse sale, which is what makes advancing it
free: the quantity is unchanged, only the turn moves. Withholding is what we
must never do, because the tape budgets hires against every coin
(`kaggriculture-champion-cash-schedule-is-load-bearing`).
"""
import copy
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / 'agents/slices/kaggriculture-most-powerful-route/variants'
CANDIDATE = VARIANTS / 'sale_timing_v4/main.py'
BASE = VARIANTS / 'sale_fert_v3/main.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prices(**items):
    return {'player': 0, 'step': 0, 'market': {'prices': dict(items)}}


@unittest.skipUnless(CANDIDATE.exists(), 'sale_timing_v4 has not been built')
class DecayDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load(CANDIDATE, 'sale_timing_unit')

    def setUp(self):
        self.policy._DECAY_HISTORY.clear()
        self.policy._DECAY_SETTINGS = {'start_step': 288, 'horizon': 6,
                                       'trigger': 0.97, 'lookback': 24}

    def feed(self, series, player=0):
        for step, row in enumerate(series):
            observation = prices(**row)
            observation['step'] = step
            observation['player'] = player
            self.policy._decay_track(observation)

    def test_a_sliding_price_is_flagged(self):
        self.feed([{'WOOL': 200 - 4 * step} for step in range(25)])
        self.assertIn('WOOL', self.policy._decay_falling(0))

    def test_a_holding_price_is_not_flagged(self):
        self.feed([{'STRAWBERRY': 220} for _ in range(25)])
        self.assertNotIn('STRAWBERRY', self.policy._decay_falling(0))

    def test_a_rising_price_is_not_flagged(self):
        self.feed([{'TOMATO': 60 + step} for step in range(25)])
        self.assertNotIn('TOMATO', self.policy._decay_falling(0))

    def test_a_slide_smaller_than_the_trigger_is_ignored(self):
        self.feed([{'EGG': 100 - step * 0.05} for step in range(25)])
        self.assertNotIn('EGG', self.policy._decay_falling(0))

    def test_nothing_is_flagged_before_a_full_lookback(self):
        self.feed([{'WOOL': 200 - 20 * step} for step in range(5)])
        self.assertEqual(self.policy._decay_falling(0), set())

    def test_a_floored_price_is_not_worth_advancing(self):
        self.feed([{'WOOL': max(1, 200 - 40 * step)} for step in range(25)])
        self.assertNotIn('WOOL', self.policy._decay_falling(0))

    def test_wheat_and_fertilizer_are_left_to_the_native_pass(self):
        self.feed([{'WHEAT': 50 - step, 'FERTILIZER': 100 - 3 * step} for step in range(25)])
        self.assertEqual(self.policy._decay_falling(0), set())

    def test_players_are_tracked_apart(self):
        self.feed([{'WOOL': 200 - 4 * step} for step in range(25)], player=0)
        self.feed([{'WOOL': 200} for step in range(25)], player=1)
        self.assertIn('WOOL', self.policy._decay_falling(0))
        self.assertNotIn('WOOL', self.policy._decay_falling(1))

    def test_history_resets_when_a_new_game_starts(self):
        self.feed([{'WOOL': 200 - 4 * step} for step in range(25)])
        self.feed([{'WOOL': 100} for _ in range(3)])
        self.assertEqual(self.policy._decay_falling(0), set())


@unittest.skipUnless(CANDIDATE.exists(), 'sale_timing_v4 has not been built')
class AdvanceOnlyTests(unittest.TestCase):
    """The layer may move a sale earlier. It may never cancel or shrink one."""

    @classmethod
    def setUpClass(cls):
        cls.policy = load(CANDIDATE, 'sale_timing_advance')

    def setUp(self):
        policy = self.policy
        policy._DECAY_HISTORY.clear()
        policy._DECAY_SETTINGS = {'start_step': 288, 'horizon': 6,
                                  'trigger': 0.97, 'lookback': 24}
        self.seen = []
        policy._DECAY_PARENT_RESERVE = lambda *a: None
        policy._LOSS_NATIVE_RESERVE = self.record
        for step in range(25):
            observation = prices(WOOL=200 - 4 * step, STRAWBERRY=220)
            observation['step'] = 400 + step
            policy._decay_track(observation)
        self.observation = observation
        policy._LOSS_OBSERVATION = observation

    def record(self, action, view, state, tape, step):
        self.seen.append((dict(view.prices), self.policy.SALE_HORIZON))
        action['market'].append(['SELL', 'WOOL', 4])

    def call(self, action, step=430):
        view = SimpleNamespace(prices=dict(self.observation['market']['prices']),
                               _sale_stock={'WOOL': 9, 'STRAWBERRY': 4})
        self.policy.reserve_sales(action, view, None, None, step)
        return view

    def test_existing_orders_are_left_untouched(self):
        action = {'farmer': ['PASS'], 'hands': [['PASS']],
                  'market': [['SELL', 'MILK', 3], ['HIRE']]}
        original = copy.deepcopy(action['market'])
        self.call(action)
        self.assertEqual(action['market'][:len(original)], original)

    def test_the_hand_count_is_never_changed(self):
        action = {'farmer': ['PASS'], 'hands': [['PASS'], ['WATER']], 'market': []}
        self.call(action)
        self.assertEqual(len(action['hands']), 2)

    def test_only_sliding_goods_are_offered_to_the_native_pass(self):
        self.call({'farmer': ['PASS'], 'hands': [], 'market': []})
        self.assertTrue(self.seen, 'the native pass was never invoked')
        offered = {item for item, price in self.seen[-1][0].items() if price >= 2}
        self.assertEqual(offered, {'WOOL'})

    def test_the_extended_horizon_is_restored_afterwards(self):
        before = self.policy.SALE_HORIZON
        self.call({'farmer': ['PASS'], 'hands': [], 'market': []})
        self.assertEqual(self.seen[-1][1], 6)
        self.assertEqual(self.policy.SALE_HORIZON, before)

    def test_the_view_price_mask_is_restored_afterwards(self):
        view = self.call({'farmer': ['PASS'], 'hands': [], 'market': []})
        self.assertEqual(view.prices, self.observation['market']['prices'])

    def test_nothing_is_advanced_before_the_start_step(self):
        action = {'farmer': ['PASS'], 'hands': [], 'market': []}
        self.call(action, step=200)
        self.assertEqual(action['market'], [])

    def test_a_full_order_book_is_never_overflowed(self):
        action = {'farmer': ['PASS'], 'hands': [],
                  'market': [['SELL', 'MILK', 1]] * self.policy.MAX_ORDERS}
        self.call(action)
        self.assertEqual(len(action['market']), self.policy.MAX_ORDERS)

    def test_a_good_already_on_the_book_is_not_offered_twice(self):
        action = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'WOOL', 2]]}
        self.call(action)
        self.assertEqual(len(action['market']), 1)

    def test_a_good_with_no_projected_stock_is_skipped(self):
        action = {'farmer': ['PASS'], 'hands': [], 'market': []}
        view = SimpleNamespace(prices=dict(self.observation['market']['prices']),
                               _sale_stock={})
        self.policy.reserve_sales(action, view, None, None, 430)
        self.assertEqual(action['market'], [])


@unittest.skipUnless(CANDIDATE.exists() and BASE.exists(), 'variants have not been built')
class DisabledParityTests(unittest.TestCase):
    """Cleared settings must reproduce the base exactly, turn for turn.

    This is the control the plan requires before any arm is read: if a disabled
    candidate already drifts, a measured margin says nothing about the arm.
    """

    def test_disabled_candidate_replays_its_base(self):
        from benchmark import run_game
        for seed in (940001, 940002):
            base = run_game(str(BASE), 'starter', seed, seat=0, diagnostics=True)
            candidate = run_game(str(CANDIDATE), 'starter', seed, seat=0, diagnostics=True,
                                 parameters={'_DECAY_SETTINGS': {'start_step': 10 ** 9,
                                                                 'horizon': 6,
                                                                 'trigger': 0.97,
                                                                 'lookback': 24}})
            for key in ('scores', 'final_shed', 'final_carried', 'hires_by_day'):
                self.assertEqual(candidate[key], base[key], f'{key} on seed {seed}')


if __name__ == '__main__':
    unittest.main()
