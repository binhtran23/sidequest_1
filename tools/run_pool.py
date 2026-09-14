#!/usr/bin/env python3
"""Run a candidate and its control against a panel of opponents, paired by seed.

Why this exists: the previous validation panel was `{our champion, our
fertilizer variant, our Astra}` — three agents we wrote ourselves — and it
required every panel to be non-negative. That rule discarded an arm worth
+3,988 coins/game to avoid a 79-coin regression against Astra, an opponent that
loses 0/8 at -15,768 to our own champion. Here each opponent carries a weight,
the decision is on the weighted mean, and an individual panel fails only on a
regression large enough to matter.

This is the *screening* metric. It rejects bad candidates cheaply. It does not
select them: local margin against agents we wrote is not leaderboard rating.
Use `tools/ladder_report.py` for that.

    python tools/run_pool.py --candidate <path> --control main.py --seeds 921700 921701
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark import run_game  # noqa: E402

# Foreign agents carry more weight than agents we wrote, because a margin
# against our own policy mostly measures how far the candidate has drifted
# from it. `public_state_router` is the only genuinely independent opponent in
# the repository; `starter` is a health check, not evidence.
DEFAULT_OPPONENTS = {
    "champion": "main.py",
    "public_state_router": "agents/slices/public-state-router/base/main.py",
    "astra": "agents/slices/astra-current/base/main.py",
}
DEFAULT_WEIGHTS = {"champion": 3.0, "public_state_router": 3.0, "astra": 1.0, "starter": 0.5}

MIN_FLOOR = 500.0
FLOOR_FRACTION = 0.05


def regression_floor(mean_margin: float) -> float:
    """How far one panel may regress before it fails on its own.

    A fixed zero threshold makes noise decisive; this scales the allowance with
    the size of the margin being measured, with an absolute minimum so a panel
    with a small margin still gets a usable band.
    """
    return -max(MIN_FLOOR, FLOOR_FRACTION * abs(mean_margin))


def panel_verdict(panels, weights=None) -> dict:
    """Accept or reject a candidate from its per-opponent paired improvements."""
    table = dict(DEFAULT_WEIGHTS if weights is None else weights)
    resolved = {p["opponent"]: float(table.get(p["opponent"], 1.0)) for p in panels}
    total = sum(resolved.values()) or 1.0
    weighted = sum(p["paired_improvement"] * resolved[p["opponent"]] for p in panels) / total
    breached = [p["opponent"] for p in panels
                if p["paired_improvement"] < regression_floor(p["mean_margin"])]
    champion = next((p for p in panels if p["opponent"] == "champion"), None)
    champion_ok = champion is None or champion["paired_improvement"] > 0
    return {"weighted_improvement": weighted, "weights": resolved, "breached": breached,
            "champion_positive": champion_ok,
            "accepted": weighted > 0 and not breached and champion_ok}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def play(agent: str, opponent: str, seeds, seats=(0, 1)) -> dict:
    """Every (seed, seat) game for one agent against one opponent."""
    games = {}
    for seed in seeds:
        for seat in seats:
            # benchmark.py patches engine globals per game, so these stay serial.
            games[(seed, seat)] = run_game(agent, opponent, seed, seat, diagnostics=True)
    return games


def compare(candidate_games, control_games, seeds, seats=(0, 1)) -> dict:
    rows = []
    for seed in seeds:
        rows.append({
            "seed": seed,
            "candidate_margin": statistics.mean(candidate_games[(seed, s)]["coin_margin"] for s in seats),
            "control_margin": statistics.mean(control_games[(seed, s)]["coin_margin"] for s in seats),
            "paired_improvement": statistics.mean(
                candidate_games[(seed, s)]["coin_margin"] - control_games[(seed, s)]["coin_margin"]
                for s in seats),
        })
    everything = list(candidate_games.values())
    return {
        "games": len(everything),
        "wins": sum(1 for g in everything if g["win"]),
        "losses": sum(1 for g in everything if not g["win"] and not g["draw"]),
        "errors": sum(1 for g in everything if g["errors"]),
        "mean_margin": statistics.mean(g["coin_margin"] for g in everything),
        "control_mean_margin": statistics.mean(g["coin_margin"] for g in control_games.values()),
        "paired_improvement": statistics.mean(r["paired_improvement"] for r in rows),
        "candidate_max_ms": max(g["max_action_ms"] for g in everything),
        "candidate_p95_ms": statistics.mean(g["p95_action_ms"] for g in everything),
        "regression_seeds": [r["seed"] for r in rows if r["paired_improvement"] < 0],
        "seeds": rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--control", default="main.py")
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--opponent", action="append", metavar="NAME=PATH",
                        help="repeatable; defaults to champion, public_state_router and astra")
    parser.add_argument("--output", default="experiments/pool")
    args = parser.parse_args(argv)

    opponents = dict(DEFAULT_OPPONENTS)
    if args.opponent:
        opponents = dict(pair.split("=", 1) for pair in args.opponent)

    panels = []
    for name, path in opponents.items():
        print(f"[pool] {name}: {len(args.seeds)} seeds x 2 seats", flush=True)
        candidate = play(args.candidate, path, args.seeds)
        control = play(args.control, path, args.seeds)
        panels.append({"opponent": name, "opponent_path": path,
                       **compare(candidate, control, args.seeds)})

    verdict = panel_verdict(panels)
    receipt = {
        "candidate": args.candidate, "candidate_sha256": _sha256(ROOT / args.candidate),
        "control": args.control, "control_sha256": _sha256(ROOT / args.control),
        "seeds": args.seeds, "seats": [0, 1],
        "panels": panels, "verdict": verdict,
    }
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "pool.json").write_text(json.dumps(receipt, indent=2) + "\n")

    print()
    print(f"{'opponent':<22}{'W-L':>10}{'margin':>12}{'control':>12}{'paired':>12}")
    for p in panels:
        print(f"{p['opponent']:<22}{f'{p[chr(119)+chr(105)+chr(110)+chr(115)]}-{p[chr(108)+chr(111)+chr(115)+chr(115)+chr(101)+chr(115)]}':>10}"
              f"{p['mean_margin']:>+12,.0f}{p['control_mean_margin']:>+12,.0f}{p['paired_improvement']:>+12,.0f}")
    print(f"\nweighted improvement {verdict['weighted_improvement']:+,.1f} coins/game — "
          f"{'ACCEPTED' if verdict['accepted'] else 'REJECTED'}")
    if verdict["breached"]:
        print(f"  regression floor breached on: {', '.join(verdict['breached'])}")
    if not verdict["champion_positive"]:
        print("  champion panel is not positive")
    return 0 if verdict["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
