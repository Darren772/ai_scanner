"""
Local JSON history log.

Each entry:
  id        str   UUID
  timestamp str   ISO 8601
  mode      str   check mode used
  result    dict  grammar / spelling / structure / tone / rewrite lists
"""

import json
import os
import uuid
import threading
from datetime import datetime

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.json")
_lock = threading.Lock()


def _load_raw() -> list:
    if not os.path.exists(_LOG_PATH):
        return []
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_raw(entries: list) -> None:
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def append(mode: str, result) -> None:
    """Append a new CheckResult to the log. Newest entry goes first."""
    with _lock:
        entries = _load_raw()
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "result": {
                "grammar":   result.grammar,
                "spelling":  result.spelling,
                "structure": result.structure,
                "tone":      result.tone,
                "rewrite":   result.rewrite,
            },
        }
        entries.insert(0, entry)
        _save_raw(entries)


def load_all() -> list:
    """Return all log entries, newest first."""
    with _lock:
        return _load_raw()


def delete(entry_id: str) -> None:
    """Delete a single entry by its UUID."""
    with _lock:
        entries = [e for e in _load_raw() if e.get("id") != entry_id]
        _save_raw(entries)


def clear() -> None:
    """Delete every log entry."""
    with _lock:
        _save_raw([])
