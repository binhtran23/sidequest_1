"""Run our own agents and freeze the games as replays the observers already read.

The crawled leader replays carry `info.TeamNames` and `info.EpisodeId`; a local
`env.toJSON()` does not. Writing those two fields in lets `analyze_leader_routes`,
`measure_sale_behaviour` and `season_curves` run over our cohort and the leaders'
with identical code, which is the only way the two columns are comparable.

Episode ids are synthesised as seed*10+seat so a rerun overwrites rather than
accumulates, and the directory always reflects one cohort.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark import run_game


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--team", required=True, help="name recorded for --agent")
    parser.add_argument("--opponent-team", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--seats", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--out", required=True, help="directory under the repo root")
    args = parser.parse_args(argv)

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for seed in args.seeds:
        for seat in args.seats:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
                scratch = Path(handle.name)
            result = run_game(args.agent, args.opponent, seed, seat, replay=str(scratch))
            if result["status"] != ["DONE", "DONE"]:
                raise RuntimeError(f"seed {seed} seat {seat} ended {result['status']}")
            replay = json.loads(scratch.read_text())
            scratch.unlink()
            names = [args.opponent_team, args.opponent_team]
            names[seat] = args.team
            episode_id = seed * 10 + seat
            replay["info"] = {"TeamNames": names, "EpisodeId": episode_id, "seed": seed}
            path = out / f"episode-{episode_id}-replay.json"
            path.write_text(json.dumps(replay))
            written.append({"episode_id": episode_id, "seed": seed, "seat": seat,
                            "coin_margin": result["coin_margin"], "path": str(path.relative_to(ROOT))})
            print(f"seed {seed} seat {seat}: margin {result['coin_margin']:+,.0f}", flush=True)

    (out / "cohort.json").write_text(json.dumps({
        "agent": args.agent, "opponent": args.opponent,
        "team": args.team, "opponent_team": args.opponent_team,
        "games": written,
    }, indent=2) + "\n")
    print(f"\nwrote {len(written)} replays to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
