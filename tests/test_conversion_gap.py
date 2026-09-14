"""The days 18-30 conversion metric that Phase 3b has to move."""
import unittest

from tools.conversion_gap import (aggregate, cash_flows, margin_at,
                                  sale_quality, summarise_game)


def game(money, sales=(), medians=None):
    """A normalised game: per-step (ours, theirs) cash plus recorded sale events."""
    return {'money': list(money), 'sales': list(sales), 'medians': dict(medians or {})}


class MarginTests(unittest.TestCase):
    def test_margin_is_our_cash_minus_theirs(self):
        self.assertEqual(margin_at(game([(100.0, 60.0), (200.0, 250.0)]), 1), -50.0)

    def test_reads_the_last_step_when_asked_beyond_the_end(self):
        self.assertEqual(margin_at(game([(100.0, 60.0), (200.0, 150.0)]), 99), 50.0)


class CashFlowTests(unittest.TestCase):
    def test_splits_a_window_into_inflow_and_outflow_per_side(self):
        rows = game([(100.0, 100.0), (150.0, 90.0), (120.0, 200.0)])
        flows = cash_flows(rows, 0, 2)
        self.assertEqual(flows['ours']['inflow'], 50.0)
        self.assertEqual(flows['ours']['outflow'], 30.0)
        self.assertEqual(flows['theirs']['inflow'], 110.0)
        self.assertEqual(flows['theirs']['outflow'], 10.0)

    def test_window_bounds_are_respected(self):
        rows = game([(0.0, 0.0), (100.0, 0.0), (200.0, 0.0), (300.0, 0.0)])
        self.assertEqual(cash_flows(rows, 2, 3)['ours']['inflow'], 100.0)

    def test_an_empty_window_reports_zero(self):
        rows = game([(0.0, 0.0), (100.0, 0.0)])
        self.assertEqual(cash_flows(rows, 1, 1)['ours']['inflow'], 0.0)


class SaleQualityTests(unittest.TestCase):
    """Price is inverse to market inventory, so when you sell is what pays."""

    def test_scores_each_side_against_the_item_median(self):
        rows = game([(0.0, 0.0)] * 3,
                    sales=[(0, 'ours', 'MILK', 60.0), (1, 'theirs', 'MILK', 120.0)],
                    medians={'MILK': 60.0})
        quality = sale_quality(rows, 0)
        self.assertAlmostEqual(quality['ours']['mean_relative_price'], 1.0)
        self.assertAlmostEqual(quality['theirs']['mean_relative_price'], 2.0)

    def test_ignores_sales_before_the_window(self):
        rows = game([(0.0, 0.0)] * 3,
                    sales=[(0, 'ours', 'MILK', 600.0), (2, 'ours', 'MILK', 60.0)],
                    medians={'MILK': 60.0})
        self.assertAlmostEqual(sale_quality(rows, 1)['ours']['mean_relative_price'], 1.0)

    def test_ignores_items_with_no_usable_median(self):
        rows = game([(0.0, 0.0)] * 2,
                    sales=[(0, 'ours', 'MILK', 60.0), (0, 'ours', 'WOOL', 10.0)],
                    medians={'MILK': 60.0, 'WOOL': 0.0})
        self.assertEqual(sale_quality(rows, 0)['ours']['events'], 1)

    def test_reports_none_when_a_side_never_sells(self):
        rows = game([(0.0, 0.0)], medians={'MILK': 60.0})
        self.assertIsNone(sale_quality(rows, 0)['ours']['mean_relative_price'])


class AggregateTests(unittest.TestCase):
    def test_separates_wins_from_losses(self):
        won = summarise_game(game([(0.0, 0.0), (500.0, 100.0)]), window_start=0)
        lost = summarise_game(game([(0.0, 0.0), (100.0, 500.0)]), window_start=0)
        report = aggregate([won, lost])
        self.assertEqual(report['wins']['games'], 1)
        self.assertEqual(report['losses']['games'], 1)
        self.assertGreater(report['wins']['mean_final_margin'], 0)
        self.assertLess(report['losses']['mean_final_margin'], 0)

    def test_reports_the_inflow_gap_that_defines_the_deficit(self):
        lost = summarise_game(game([(0.0, 0.0), (100.0, 500.0)]), window_start=0)
        report = aggregate([lost])
        self.assertAlmostEqual(report['losses']['mean_inflow_gap'], -400.0)

    def test_an_empty_cohort_does_not_crash(self):
        self.assertEqual(aggregate([])['losses']['games'], 0)


if __name__ == '__main__':
    unittest.main()
