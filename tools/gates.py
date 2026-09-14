"""Absolute callback-latency budget shared by the promotion gates.

The engine allows one second per callback (`actTimeout: 1` in the packaged
`kaggriculture.json`). The earlier gates instead required a candidate to be no
slower on average than the agent it replaced. That is a comparison against a
moving target with no competition meaning: it rejected `loss_upgrade_v1` for
being 1.6 microseconds per callback slower than the champion, 0.00016% of the
allowance. The budget below is absolute, so a candidate is judged on whether it
fits the engine's limit rather than on whether it beats yesterday's build.

The margins are deliberately wide. Kaggle's workers are slower and noisier than
a local run, so p95 carries a 20x margin over the engine's per-callback limit
and the maximum carries 5x.
"""
from __future__ import annotations

ACT_TIMEOUT_MS = 1000.0
P95_BUDGET_MS = 50.0
MAX_BUDGET_MS = 200.0


def latency_within_budget(p95_ms: float, max_ms: float) -> bool:
    """True when a callback profile fits the competition budget with margin."""
    return p95_ms < P95_BUDGET_MS and max_ms < MAX_BUDGET_MS
