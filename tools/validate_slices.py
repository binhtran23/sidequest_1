"""Static provenance and entrypoint validation; intentionally never imports sources."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_slice(path):
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    raw = ROOT / manifest["raw_path"]
    if not raw.is_file() or sha256(raw) != manifest["raw_sha256"]:
        raise ValueError(f"raw checksum mismatch: {path.name}")
    relative_file, symbol = manifest["entrypoint"].split(":", 1)
    entrypoint = path / relative_file
    tree = ast.parse(entrypoint.read_text(), filename=str(entrypoint))
    if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol for node in tree.body):
        raise ValueError(f"missing entrypoint {symbol}: {path.name}")
    for reference in manifest.get("development", {}).get("variant_entrypoints", []):
        relative, variant_symbol = reference.split(":", 1)
        variant_path = path / relative
        variant_tree = ast.parse(variant_path.read_text(), filename=str(variant_path))
        if not any(isinstance(node, ast.FunctionDef) and node.name == variant_symbol for node in variant_tree.body):
            raise ValueError(f"missing variant entrypoint: {reference}")
    return {"source_id": manifest["source_id"], "ok": True, "raw_sha256": manifest["raw_sha256"]}


def main():
    slices = ROOT / "agents" / "slices"
    results = [validate_slice(path) for path in sorted(slices.iterdir()) if (path / "manifest.json").is_file()]
    print(json.dumps({"slices": results}, indent=2))


if __name__ == "__main__":
    main()
