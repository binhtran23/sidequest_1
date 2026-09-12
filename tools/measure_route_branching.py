"""Per-step branching profile: how many distinct unit-action variants across a cohort."""
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/binhtran23/Documents/Kaggle Compe/kaggriculture")


def tapes_from_snapshot(snapshot):
    m = json.loads((ROOT / "experiments" / snapshot / "manifest.json").read_text())
    seats = {int(a["episode_id"]): int(a["seat"]) for a in m["cohort"]["associations"]}
    out = {}
    for r in m["raw_files"]:
        eid = int(r["episode_id"]); s = seats[eid]
        rep = json.loads((ROOT / r["path"]).read_text())
        out[eid] = [rep["steps"][i + 1][s]["action"] for i in range(len(rep["steps"]) - 1)]
    return out


def tapes_from_dir(directory, team):
    out = {}
    for p in sorted((ROOT / directory).glob("episode-*-replay.json")):
        rep = json.loads(p.read_text())
        s = rep["info"]["TeamNames"].index(team)
        out[rep["info"]["EpisodeId"]] = [rep["steps"][i + 1][s]["action"] for i in range(len(rep["steps"]) - 1)]
    return out


def profile(tapes):
    ids = sorted(tapes); n = len(ids)
    length = min(len(tapes[i]) for i in ids)
    variants, consensus = [], []
    for step in range(length):
        counts = Counter(
            json.dumps([tapes[i][step].get("farmer"), tapes[i][step].get("hands")], sort_keys=True)
            for i in ids)
        variants.append(len(counts))
        consensus.append(counts.most_common(1)[0][1] / n)
    return variants, consensus


def report(name, tapes):
    variants, consensus = profile(tapes)
    print(f"\n===== {name} ({len(tapes)} episodes, {len(variants)} steps) =====")
    first = next((i for i, v in enumerate(variants) if v > 1), None)
    print(f"first branching step: {first}")
    for thr in (0.9, 0.5, 0.25):
        s = next((i for i, c in enumerate(consensus) if c < thr), None)
        print(f"first step where modal action held by <{thr:.0%} of episodes: {s}")
    print(f"mean distinct variants per step: {sum(variants)/len(variants):.2f} of {len(tapes)}")
    print("\n day  steps   mean variants  mean consensus")
    for day in range(30):
        lo, hi = day * 24, min((day + 1) * 24, len(variants))
        if lo >= len(variants):
            break
        v = variants[lo:hi]; c = consensus[lo:hi]
        bar = "#" * round(sum(v) / len(v))
        print(f"{day:>4} {lo:>4}-{hi-1:<4} {sum(v)/len(v):>10.2f}  {sum(c)/len(c):>13.2f}  {bar}")


report("Majkel1337 (leader)", tapes_from_snapshot("top-replays-20260912T115205202783Z"))
report("our champion", tapes_from_dir("evidence/raw/champion-losses-20260912", "Bình Trần Thanh"))
