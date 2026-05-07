from __future__ import annotations
import json
from pathlib import Path


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True))


def _src(state: dict, source: str) -> dict:
    return state.setdefault(source, {"consecutive_failures": 0, "alerted": False})


def record_result(state: dict, source: str, ok: bool) -> dict:
    s = _src(state, source)
    if ok:
        s["consecutive_failures"] = 0
        s["alerted"] = False
    else:
        s["consecutive_failures"] += 1
    return state


def should_alert(state: dict, source: str, threshold: int = 3) -> bool:
    s = _src(state, source)
    if s["consecutive_failures"] < threshold:
        return False
    if s["alerted"]:
        return False
    s["alerted"] = True
    return True
