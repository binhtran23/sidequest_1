"""Development wrapper around the extracted public Router policy."""
import importlib.util
from pathlib import Path

from agents.shared.adaptive import TelemetryRecorder, adapt_action_dict

_BASE_PATH = Path(__file__).resolve().parents[2] / "base" / "main.py"
_SPEC = importlib.util.spec_from_file_location("public_state_router_base", _BASE_PATH)
base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(base)
_TELEMETRY = TelemetryRecorder()

def agent(obs, configuration=None):
    return adapt_action_dict(obs, base.agent(obs), _TELEMETRY)

def drain_telemetry():
    return _TELEMETRY.drain()
