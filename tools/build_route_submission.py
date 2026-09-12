"""Construct a deterministic self-contained source from the audited router.

Prints a patch for review/application, or checks that a staged source matches.
Does not execute source code, promote, or upload anything.
"""
import argparse
import ast
import base64
import hashlib
import json
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "agents/slices/kaggriculture-most-powerful-route/base"
TARGET = BASE.parent / "variants/submission_v1/main.py"


def source():
    expected = {"router.py":"3a444a70ea9dd89f3cb857676fcc0180ebf1dfb7ede89f7f0cc82a2ef384e380",
                "actions.json":"17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef"}
    for name, checksum in expected.items():
        if hashlib.sha256((BASE / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("Audited input changed: " + name)
    code = (BASE / "router.py").read_text()
    payload = base64.b85encode(zlib.compress((BASE / "actions.json").read_bytes(), 9)).decode()
    encoded = "\n".join("    " + repr(payload[i:i+100]) for i in range(0, len(payload), 100))
    replacements = {
        "from pathlib import Path\n": "import zlib\n",
        "_INLINE_TAPES = json.loads((Path(__file__).resolve().parent / 'actions.json').read_text(encoding='utf-8'))":
            "_INLINE_TAPES = json.loads(zlib.decompress(base64.b85decode(\n" + encoded + "\n)))",
        "self.tapes = copy.deepcopy(_INLINE_TAPES)": "self.tapes = _INLINE_TAPES  # Read-only; each emitted action is copied below.",
        "        # Kaggle's source loader omits __file__, but retains the code filename.\n        folder = Path(agent.__code__.co_filename).resolve().parent\n        _POLICY = Policy(folder)":
            "        _POLICY = Policy(None)",
        "SALE_HORIZON = 2": "SALE_HORIZON = 3",
    }
    for old, new in replacements.items():
        if code.count(old) != 1:
            raise ValueError("Unexpected source anchor: " + old[:80])
        code = code.replace(old, new, 1)
    header = "# SPDX-License-Identifier: Apache-2.0\n# Modified 2026-09-12: self-contained Route test v1; three-turn sale window.\n"
    code = header + code + '''

# Development benchmarking can drain these events; the agent requires no logger.
_SUBMISSION_SALE_EVENTS = []
_SUBMISSION_RESERVE = reserve_sales

def reserve_sales(action, view, state, tape, step):
    before = len(action['market'])
    _SUBMISSION_RESERVE(action, view, state, tape, step)
    for order in action['market'][before:]:
        _SUBMISSION_SALE_EVENTS.append({'type': 'strategy_decision',
            'hypothesis': 'sale_horizon', 'turn': step, 'horizon': 3,
            'item': order[1], 'quantity': order[2]})

def drain_telemetry():
    events = list(_SUBMISSION_SALE_EVENTS)
    _SUBMISSION_SALE_EVENTS.clear()
    return events
'''
    code += "\n# Preserved upstream licensing and attribution.\n"
    code += "LICENSE_TEXT = " + repr((BASE / "LICENSE.txt").read_text()) + "\n"
    code += "NOTICE_TEXT = " + repr((BASE / "NOTICE.txt").read_text()) + "\n"
    code += "\n# Kaggle chooses the last inserted callable in the executed namespace.\n_KAGGLE_ENTRYPOINT = agent\n"
    tree = ast.parse(code)
    allowed = {"copy", "json", "collections", "base64", "lzma", "zlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(n.name in allowed for n in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module in allowed
    assert "__file__" not in code and "read_text(" not in code and "open(" not in code
    return code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    code = source()
    if args.check:
        assert TARGET.read_text() == code
        print(json.dumps({"path":str(TARGET.relative_to(ROOT)), "sha256":hashlib.sha256(code.encode()).hexdigest(), "bytes":len(code.encode())}))
    else:
        if TARGET.exists():
            print("*** Begin Patch\n*** Update File: " + str(TARGET) + "\n@@")
            print("\n".join("-" + line for line in TARGET.read_text().splitlines()))
        else:
            print("*** Begin Patch\n*** Add File: " + str(TARGET))
        print("\n".join("+" + line for line in code.splitlines()))
        print("*** End Patch")


if __name__ == "__main__":
    main()
