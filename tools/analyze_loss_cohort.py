"""Audit loss mechanisms from frozen public replays; never execute replay code.

Opponent private data is used only for offline evidence. All events align
observation[t] with action[t+1]. Reports distinguish observation from causation.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from tools.top_replays.api import sha256_file

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}
# Audited against kaggle-environments 1.32.7; ongoing yield is finite.
CROPS = {"WHEAT": (2, 4, 0, 6), "CARROT": (2, 3, 0, 4),
         "MELON": (10, 12, 0, 6), "TOMATO": (8, 8, 1, 4),
         "STRAWBERRY": (10, 10, 2, 4)}


def useful_days(tile, day):
    """Potential new fertilizer bonus days; watering/harvest are not assumed."""
    first, maximum, interval, cap = CROPS[tile["crop"]]
    result = []
    for d in range(day, min(day + 3, 30)):
        if tile.get("fertilized_until_day", -1) >= d:
            continue
        age = d - tile["planted_day"]
        if interval:
            production = age + 1 - first
            eligible = production >= 0 and production % interval == 0 and production // interval < cap
        else:
            eligible = ((maximum + 1) // 2 <= age <= maximum
                        and tile.get("yield_units", 0) < cap
                        and (d != day or not tile.get("watered_today")))
        if eligible:
            result.append(d)
    return result


def analyze_seat(replay, seat):
    counts, daily, events = Counter(), defaultdict(Counter), []
    margins, checkpoints = [], []
    steps = replay["steps"]
    for t, states in enumerate(steps):
        obs = states[seat]["observation"]
        farm = obs["farms"][seat]
        day = int(obs["day"])
        money = farm["money"]
        margin = money - obs["farms"][1-seat]["money"]
        margins.append(margin)
        if t % 24 == 0 or t == len(steps)-1:
            assets = Counter(tile.get("crop") or tile.get("animal") for row in farm["tiles"]
                             for tile in row if isinstance(tile, dict) and (tile.get("crop") or tile.get("animal")))
            checkpoints.append({"step": t, "money": money, "margin": margin, "assets": dict(assets)})
        if t == len(steps)-1:
            continue
        after = steps[t+1][seat]["observation"]
        action = steps[t+1][seat].get("action") or {}
        positions = [farm["farmer"], *farm["hands"]]
        commands = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        inventories = obs["private"]["inventories"]
        if len(commands) != len(positions):
            counts["hand_mismatch"] += 1
        harvested = set()
        for unit, (pos, command) in enumerate(zip(positions, commands)):
            if not command:
                continue
            op = command[0]
            counts[op] += 1
            daily[day][op] += 1
            x, y = pos
            tile = farm["tiles"][y][x]
            inv = inventories[unit] if unit < len(inventories) else {}
            if op == "FERTILIZE":
                valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and inv.get("FERTILIZER", 0) > 0
                if not valid:
                    counts["invalid_fertilizer"] += 1
                else:
                    counts["fertilizer_" + tile["crop"]] += 1
                    if not useful_days(tile, day):
                        counts["fertilizer_without_new_window"] += 1
                        events.append({"step": t, "event": "fertilizer_without_new_window", "tile": pos, "crop": tile["crop"]})
            if op == "FEED" and isinstance(tile, dict) and tile.get("animal") and not inv.get("WHEAT", 0):
                counts["empty_feed"] += 1
                events.append({"step": t, "event": "empty_feed", "tile": pos})
            if op == "HARVEST" and isinstance(tile, dict) and tuple(pos) not in harvested:
                crop = tile.get("crop")
                mature = not crop or day - tile["planted_day"] >= CROPS[crop][0]
                quantity = tile.get("yield_units", 0) if mature else 0
                item = crop or PRODUCT.get(tile.get("animal"))
                if item and quantity:
                    counts["harvest_units"] += quantity
                    counts["harvest_" + item] += quantity
                    daily[day]["harvest_" + item] += quantity
                    harvested.add(tuple(pos))
        for order in action.get("market", []):
            if order and order[0] == "HIRE":
                daily[day]["hire_requests"] += 1
        daily[day]["net_cash"] += after["farms"][seat]["money"] - money
        if int(after["day"]) != day:
            for y, row in enumerate(farm["tiles"]):
                for x, tile in enumerate(row):
                    if not isinstance(tile, dict):
                        continue
                    new = after["farms"][seat]["tiles"][y][x]
                    if tile.get("animal") and (not isinstance(new, dict) or not new.get("animal")):
                        counts["animal_loss"] += 1
                        events.append({"step": t+1, "event": "animal_loss", "tile": [x,y]})
                    if tile.get("crop") and isinstance(new, dict) and new.get("kind") == "WEED":
                        counts["crop_to_weed"] += 1
                        events.append({"step": t+1, "event": "crop_to_weed", "tile": [x,y]})
    final_private = steps[-1][seat]["observation"]["private"]
    counts["terminal_inventory"] = sum(final_private["shed"].values()) + sum(sum(i.values()) for i in final_private["inventories"])
    erosion = [{"from_step": a["step"], "to_step": b["step"], "margin_change": b["margin"]-a["margin"]}
               for a,b in zip(checkpoints, checkpoints[1:])]
    return {"counts": dict(counts), "days": dict(daily), "events": events,
            "checkpoints": checkpoints, "margins": margins,
            "worst_erosion": min(erosion, key=lambda r:r["margin_change"]) if erosion else None}


def build_report(manifest, root=ROOT):
    records = {r["episode_id"]: r for r in manifest["raw_files"]}
    by_episode = defaultdict(list)
    for a in manifest["cohort"]["associations"]:
        by_episode[a["episode_id"]].append(a)
    rows = []
    for episode_id, associations in by_episode.items():
        record = records.get(episode_id)
        if record is None:
            continue
        path = root / record["path"]
        if sha256_file(path) != record["sha256"]:
            raise ValueError(f"Replay checksum mismatch: {path}")
        replay = json.loads(path.read_text())
        if replay.get("module_version") != "1.32.7":
            raise ValueError(f"Audit new engine semantics before analysis: {replay.get('module_version')}")
        both = [analyze_seat(replay, seat) for seat in (0,1)]
        for a in associations:
            seat = a["seat"]
            margin = both[seat]["margins"][-1]
            row = {**a, "seed": replay["info"]["seed"], "engine": replay["module_version"],
                   "statuses": replay["statuses"], "technical_failure": any(s != "DONE" for s in replay["statuses"]),
                   "final_margin": margin, "result": "win" if margin > 0 else "loss" if margin < 0 else "draw",
                   "shops": replay["steps"][-1][seat]["observation"]["town"]["unlocked_shops"],
                   "own": both[seat], "opponent": both[1-seat]}
            rows.append(row)
    # Same-submission controls, matched on public shop sequence, then recency.
    for row in rows:
        if row["result"] != "loss" or row["technical_failure"]:
            continue
        wins = [r for r in rows if r["submission_id"] == row["submission_id"] and r["result"] == "win" and not r["technical_failure"]]
        def distance(r):
            return (sum(a != b for a,b in zip(r["shops"][:2],row["shops"][:2])),
                    sum(a != b for a,b in zip(r["shops"],row["shops"])),
                    abs(r["episode_id"]-row["episode_id"]),r["episode_id"])
        if wins:
            match = min(wins, key=distance)
            row["matched_win"] = {"episode_id": match["episode_id"],
                                  "opening_shop_mismatches": distance(match)[0],
                                  "shop_mismatches": distance(match)[1]}
    batches = []
    for size in (15,30,50):
        groups = []
        for team in manifest["cohort"]["teams"]:
            eligible = sorted((r for r in rows if r["team_id"] == team["team_id"]), key=lambda r:(r["end_time"],r["episode_id"]), reverse=True)[:size]
            for result in ("win","loss","draw"):
                selected = [r for r in eligible if r["result"] == result]
                if not selected:
                    continue
                keys = {k for r in selected for k in r["own"]["counts"]}
                groups.append({"team": team["team_name"], "result": result, "games": len(selected),
                               "mean_margin": statistics.mean(r["final_margin"] for r in selected),
                               "own_mean": {k:statistics.mean(r["own"]["counts"].get(k,0) for r in selected) for k in sorted(keys)},
                               "opponent_mean": {k:statistics.mean(r["opponent"]["counts"].get(k,0) for r in selected) for k in sorted(keys)}})
        batches.append({"per_team_limit": size, "groups": groups})
    return {"snapshot": manifest["snapshot_id"], "analysis_tool_sha256": sha256_file(Path(__file__)),
            "downloaded_episodes":len(records),
            "expected_episodes":len(by_episode), "associations":len(rows),
            "complete": len(records)==len(by_episode), "batches":batches, "matches":rows,
            "limitations": ["Latest-match opponent-selected sample, not ladder win-rate evidence.",
                            "Cross-game prices and opponents confound comparisons; matched wins may use different shops.",
                            "Fertilizer windows are potential opportunities, not observed marginal profit.",
                            "Harvest quantities use pre-action tiles and deduplicate shared tiles; same-turn watering may add yield.",
                            "Offline opponent private inventory is excluded from candidate inputs."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    folder = ROOT / "experiments" / args.snapshot
    manifest = json.loads((folder/"manifest.json").read_text())
    report = build_report(manifest)
    (folder/"loss-analysis.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("matches","batches")}, indent=2))
    for group in report["batches"][-1]["groups"]:
        print(group["team"],group["result"],group["games"],round(group["mean_margin"]),
              {k:round(group["own_mean"].get(k,0),1) for k in ("FERTILIZE","fertilizer_without_new_window","harvest_units","animal_loss","crop_to_weed","terminal_inventory")})


if __name__ == "__main__":
    main()
