"""
log.py — Load and persist snoop_log data.

Two stores:
  - sessions.json: raw training session logs (what happened each session)
  - behaviors.json: the dog's current learned associations (trigger → action)
"""

import json
from pathlib import Path

DIR = Path(__file__).parent
SESSIONS_PATH = DIR / "sessions.json"
BEHAVIORS_PATH = DIR / "behaviors.json"


# --- Sessions ---

def load_sessions(path: Path = SESSIONS_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def append_session(entry: dict, path: Path = SESSIONS_PATH) -> None:
    sessions = load_sessions(path)
    sessions.append(entry)
    with open(path, "w") as f:
        json.dump(sessions, f, indent=2)


def next_session_id(path: Path = SESSIONS_PATH) -> int:
    return len(load_sessions(path)) + 1


# --- Behaviors ---

def load_behaviors(path: Path = BEHAVIORS_PATH) -> list[dict]:
    """Load the dog's current learned behavior associations."""
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_behaviors(behaviors: list[dict], path: Path = BEHAVIORS_PATH) -> None:
    with open(path, "w") as f:
        json.dump(behaviors, f, indent=2)
