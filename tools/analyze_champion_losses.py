"""Observe a frozen local Kaggle replay cohort; never alter an agent or replay.

Replay state t contains the result/action from callback t-1. Use state t's
observation with state t+1's action, and restore the omitted shared step field.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "evidence/raw/champion-losses-20260912"
OUT = ROOT / "experiments/champion-losses-20260912"
CHAMPION = ROOT / "agents/slices/kaggriculture-most-powerful-route/base/main.py"
TEAM = "Bình Trần Thanh"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assets(farm):
    return dict(Counter(t.get("animal") or t.get("crop") or t["kind"]
                        for row in farm["tiles"] for t in row if isinstance(t, dict)))


def observe(replay, seat, step):
    obs = copy.deepcopy(replay["steps"][step][seat]["observation"])
    obs["step"] = step
    obs["player"] = seat
    return obs


def analyze(path):
    replay = json.loads(path.read_text())
    seat = replay["info"]["TeamNames"].index(TEAM)
    spec = importlib.util.spec_from_file_location("champion_audit", CHAMPION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    margins, days, mismatches, events = [], [], [], []
    sales = [Counter(), Counter()]
    first_action_difference = None
    for step, states in enumerate(replay["steps"]):
        obs = observe(replay, seat, step)
        farms = obs["farms"]
        margin = farms[seat]["money"] - farms[1-seat]["money"]
        margins.append(margin)
        if step % 24 == 0 or step == len(replay["steps"])-1:
            days.append({"step": step, "day": obs["day"], "hour": obs["hour"],
                         "margin": margin, "money": [f["money"] for f in farms],
                         "assets": [assets(f) for f in farms],
                         "prices": obs["market"]["prices"],
                         "shops": obs["town"]["unlocked_shops"],
                         "sale_requested_cumulative": [dict(v) for v in sales]})
        if step + 1 == len(replay["steps"]):
            continue
        next_states = replay["steps"][step+1]
        actual = next_states[seat]["action"]
        predicted = module.agent(copy.deepcopy(obs), replay["configuration"])
        if predicted != actual:
            mismatches.append({"step": step, "expected": predicted, "actual": actual})
        if first_action_difference is None and actual != next_states[1-seat]["action"]:
            first_action_difference = step
        for player in (0, 1):
            for order in (next_states[player]["action"] or {}).get("market", []):
                if order and order[0] == "SELL":
                    try:
                        sales[player][order[1]] += int(order[2])
                    except (ValueError, TypeError, IndexError):
                        sales[player][order[1] + "_non_numeric_orders"] += 1
            if step % 24 == 23:
                before, after = farms[player], next_states[player]["observation"]["farms"][player]
                for y, row in enumerate(before["tiles"]):
                    for x, tile in enumerate(row):
                        if not isinstance(tile, dict):
                            continue
                        new = after["tiles"][y][x]
                        if tile.get("animal") and (not isinstance(new, dict) or not new.get("animal")):
                            events.append({"step": step+1, "seat": player, "event": "animal_removed",
                                           "asset": tile["animal"], "tile": [x,y]})
                        if tile.get("crop") and isinstance(new, dict) and new.get("kind") == "WEED":
                            events.append({"step": step+1, "seat": player, "event": "crop_to_weed",
                                           "asset": tile["crop"], "tile": [x,y]})
    final_margin = margins[-1]
    permanent = next((i for i in range(len(margins)) if max(margins[i:]) < 0), None)
    first_24 = next((i for i in range(len(margins)-23) if max(margins[i:i+24]) < 0), None)
    erosion = [{"from_step": a["step"], "to_step": b["step"],
                "margin_change": b["margin"]-a["margin"]} for a,b in zip(days,days[1:])]
    return {"episode_id": replay["info"]["EpisodeId"], "seat": seat,
            "opponent": replay["info"]["TeamNames"][1-seat], "seed": replay["info"]["seed"],
            "module_version": replay["module_version"], "statuses": replay["statuses"],
            "final_margin": final_margin, "rewards": replay["rewards"],
            "first_action_difference_between_players": first_action_difference,
            "first_24_turn_deficit": first_24, "permanent_deficit_step": permanent,
            "worst_day_erosion": min(erosion,key=lambda v:v["margin_change"]),
            "champion_action_mismatch_count": len(mismatches), "mismatch_examples": mismatches[:3],
            "days": days, "events": events, "margins": margins,
            "path": str(path.relative_to(ROOT)), "sha256": digest(path)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(RAW.glob("episode-*-replay.json"), reverse=True)
    if len(files) != 15:
        raise ValueError("This frozen analysis requires exactly 15 replay files")
    manifest = {"submission_id": 56163729, "cohort": "15 latest completed public episodes at initial query on 2026-09-12",
                "source": "kaggle competitions episodes 56163729; kaggle competitions replay <id>",
                "raw_files": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in files],
                "champion_files": {str(p.relative_to(ROOT)): digest(p) for p in sorted(CHAMPION.parent.iterdir()) if p.is_file()},
                "action_alignment": "observation[t] -> action[t+1]; turns are zero-based"}
    manifest_path = OUT / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        for key in ("raw_files", "champion_files"):
            if previous[key] != manifest[key]:
                raise ValueError(f"Frozen evidence changed: {key}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    results = []
    for path in files:
        item = analyze(path)
        results.append(item)
        print(json.dumps({k:v for k,v in item.items() if k not in {"days","events","margins","mismatch_examples"}}), flush=True)
    (OUT / "analysis.json").write_text(json.dumps(results, indent=2)+"\n")


if __name__ == "__main__":
    main()
