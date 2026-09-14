"""The ladder metric: rating-adjusted strength from real episode outcomes."""
import unittest

from tools.ladder_report import (band_summary, bootstrap_equilibrium,
                                 episode_rows, equilibrium_rating)


def episode(episode_id, my_sub, my_reward, opp_reward, opp_team, seat=0,
            state='COMPLETED', end='2026-09-13T10:00:00Z'):
    agents = [{'submission_id': my_sub, 'index': seat, 'reward': my_reward, 'team_id': 1},
              {'submission_id': 999, 'index': 1 - seat, 'reward': opp_reward,
               'team_id': opp_team, 'team_name': f'team-{opp_team}'}]
    return {'id': episode_id, 'state': state, 'type': 'PUBLIC', 'end_time': end,
            'agents': sorted(agents, key=lambda a: a['index'])}


class EpisodeRowTests(unittest.TestCase):
    def test_extracts_seat_margin_and_opponent(self):
        rows = episode_rows([episode(1, 500, 1200.0, 1000.0, 77, seat=1)], 500)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['seat'], 1)
        self.assertEqual(rows[0]['margin'], 200.0)
        self.assertTrue(rows[0]['won'])
        self.assertEqual(rows[0]['opponent_team_id'], 77)

    def test_skips_unfinished_and_unscored_episodes(self):
        episodes = [episode(1, 500, 1.0, 2.0, 77, state='RUNNING'),
                    episode(2, 500, None, 2.0, 77),
                    episode(3, 500, 2.0, 1.0, 77)]
        self.assertEqual([r['episode_id'] for r in episode_rows(episodes, 500)], [3])

    def test_ignores_episodes_that_are_not_ours(self):
        self.assertEqual(episode_rows([episode(1, 501, 2.0, 1.0, 77)], 500), [])

    def test_deduplicates_repeated_episode_ids(self):
        rows = episode_rows([episode(1, 500, 2.0, 1.0, 77), episode(1, 500, 2.0, 1.0, 77)], 500)
        self.assertEqual(len(rows), 1)


class BandTests(unittest.TestCase):
    def setUp(self):
        # Five wins against 2000-rated teams, one win and three losses at 2500.
        self.rows = ([{'won': True, 'margin': 100.0, 'opponent_team_id': 10}] * 5 +
                     [{'won': True, 'margin': 50.0, 'opponent_team_id': 20}] +
                     [{'won': False, 'margin': -50.0, 'opponent_team_id': 20}] * 3)
        self.ratings = {10: 2000.0, 20: 2500.0}

    def test_summarises_each_band(self):
        bands = band_summary(self.rows, self.ratings, [(1900, 2100), (2400, 2600)])
        self.assertEqual(bands[0]['games'], 5)
        self.assertEqual(bands[0]['wins'], 5)
        self.assertEqual(bands[1]['games'], 4)
        self.assertEqual(bands[1]['wins'], 1)
        self.assertAlmostEqual(bands[1]['win_rate'], 0.25)

    def test_drops_opponents_missing_from_the_leaderboard(self):
        rows = self.rows + [{'won': True, 'margin': 1.0, 'opponent_team_id': 999}]
        bands = band_summary(rows, self.ratings, [(0, 9999)])
        self.assertEqual(bands[0]['games'], 9)


class EquilibriumTests(unittest.TestCase):
    def test_even_record_against_one_rating_returns_that_rating(self):
        rows = ([{'won': True, 'opponent_team_id': 1}] * 10 +
                [{'won': False, 'opponent_team_id': 1}] * 10)
        self.assertAlmostEqual(equilibrium_rating(rows, {1: 2400.0}), 2400.0, places=1)

    def test_beating_stronger_opponents_raises_the_estimate(self):
        weak = ([{'won': True, 'opponent_team_id': 1}] * 10 +
                [{'won': False, 'opponent_team_id': 1}] * 10)
        strong = ([{'won': True, 'opponent_team_id': 2}] * 10 +
                  [{'won': False, 'opponent_team_id': 2}] * 10)
        ratings = {1: 2000.0, 2: 2800.0}
        self.assertLess(equilibrium_rating(weak, ratings),
                        equilibrium_rating(strong, ratings))

    def test_is_monotone_in_wins(self):
        ratings = {1: 2400.0}
        losing = ([{'won': True, 'opponent_team_id': 1}] * 5 +
                  [{'won': False, 'opponent_team_id': 1}] * 15)
        winning = ([{'won': True, 'opponent_team_id': 1}] * 15 +
                   [{'won': False, 'opponent_team_id': 1}] * 5)
        self.assertLess(equilibrium_rating(losing, ratings), 2400.0)
        self.assertGreater(equilibrium_rating(winning, ratings), 2400.0)

    def test_an_unbeaten_record_is_reported_as_a_lower_bound(self):
        rows = [{'won': True, 'opponent_team_id': 1}] * 10
        self.assertIsNone(equilibrium_rating(rows, {1: 2400.0}, bounded_only=True))

    def test_bootstrap_interval_brackets_the_point_estimate(self):
        rows = ([{'won': True, 'opponent_team_id': 1}] * 30 +
                [{'won': False, 'opponent_team_id': 1}] * 30)
        ratings = {1: 2400.0}
        point = equilibrium_rating(rows, ratings)
        low, high = bootstrap_equilibrium(rows, ratings, draws=200)
        self.assertLessEqual(low, point)
        self.assertLessEqual(point, high)

    def test_bootstrap_is_deterministic(self):
        rows = ([{'won': True, 'opponent_team_id': 1}] * 20 +
                [{'won': False, 'opponent_team_id': 1}] * 20)
        ratings = {1: 2400.0}
        self.assertEqual(bootstrap_equilibrium(rows, ratings, draws=100),
                         bootstrap_equilibrium(rows, ratings, draws=100))


if __name__ == '__main__':
    unittest.main()
