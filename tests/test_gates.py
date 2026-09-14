"""The promotion gates must measure the competition, not the incumbent."""
import unittest

from tools.gates import (ACT_TIMEOUT_MS, MAX_BUDGET_MS, P95_BUDGET_MS,
                         latency_within_budget)
from tools.report_loss_validation import evaluate_gates

# Measured for loss_upgrade_v1 in experiments/loss-upgrade-validation-20260912.
# The candidate is 1.6 microseconds per callback slower than the champion and
# was rejected for it; both profiles are four orders of magnitude inside budget.
CANDIDATE_MEAN_MS = 0.03870833333333333
BASELINE_MEAN_MS = 0.037125
CANDIDATE_P95_MS = 0.0616875
CANDIDATE_MAX_MS = 7.808


def panel(opponent, **overrides):
    base = {'opponent': opponent, 'mean_margin': 2535.0, 'paired_improvement': 32.0,
            'candidate_mean_ms': CANDIDATE_MEAN_MS, 'baseline_mean_ms': BASELINE_MEAN_MS,
            'candidate_p95_ms': CANDIDATE_P95_MS, 'candidate_max_ms': CANDIDATE_MAX_MS,
            'candidate_telemetry_events': 3536}
    base.update(overrides)
    return base


def panels(**overrides):
    return [panel('champion', **overrides), panel('fertilizer', **overrides),
            panel('astra', **overrides)]


class BudgetTests(unittest.TestCase):
    def test_budgets_sit_well_inside_the_engine_timeout(self):
        self.assertLess(MAX_BUDGET_MS, ACT_TIMEOUT_MS / 4)
        self.assertLess(P95_BUDGET_MS, MAX_BUDGET_MS)

    def test_accepts_the_profile_that_the_old_gate_rejected(self):
        self.assertTrue(latency_within_budget(CANDIDATE_P95_MS, CANDIDATE_MAX_MS))

    def test_being_slower_than_the_incumbent_is_not_a_failure(self):
        self.assertTrue(latency_within_budget(BASELINE_MEAN_MS * 100, CANDIDATE_MAX_MS))

    def test_rejects_a_candidate_that_is_genuinely_slow(self):
        self.assertFalse(latency_within_budget(P95_BUDGET_MS + 1, CANDIDATE_MAX_MS))

    def test_rejects_a_spiky_candidate_with_a_healthy_p95(self):
        self.assertFalse(latency_within_budget(CANDIDATE_P95_MS, MAX_BUDGET_MS + 1))


class ValidationGateTests(unittest.TestCase):
    def test_the_frozen_r7_panels_now_validate(self):
        gates = evaluate_gates(panels())
        self.assertTrue(gates['latency_within_budget'])
        self.assertTrue(all(gates.values()), gates)

    def test_latency_gate_fails_when_a_single_panel_blows_the_budget(self):
        rows = panels()
        rows[2]['candidate_max_ms'] = MAX_BUDGET_MS + 1
        self.assertFalse(evaluate_gates(rows)['latency_within_budget'])

    def test_the_old_mean_comparison_is_gone(self):
        self.assertNotIn('no_mean_runtime_regression', evaluate_gates(panels()))

    def test_champion_improvement_still_required(self):
        rows = panels()
        rows[0]['mean_margin'] = -1.0
        self.assertFalse(evaluate_gates(rows)['positive_champion_improvement'])

    def test_opponent_regression_still_required(self):
        rows = panels()
        rows[1]['paired_improvement'] = -1.0
        self.assertFalse(evaluate_gates(rows)['no_aggregate_opponent_regression'])

    def test_telemetry_still_required(self):
        rows = panels()
        rows[1]['candidate_telemetry_events'] = 0
        self.assertFalse(evaluate_gates(rows)['zero_errors_complete_telemetry'])


if __name__ == '__main__':
    unittest.main()
