"""Experimental tomato_only entrypoint; not a promoted submission."""
import importlib.util
import json
from pathlib import Path

_FOLDER = Path(__file__).resolve().parent
_PATH = _FOLDER.parent / "test_v1/policy.py"
_SPEC = importlib.util.spec_from_file_location("route_test_policy", _PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
_POLICY = _MODULE.TestPolicy(json.loads((_FOLDER / "settings.json").read_text()))

def agent(observation, configuration=None):
    return _POLICY.agent(observation, configuration)

def drain_telemetry():
    return _POLICY.drain()
