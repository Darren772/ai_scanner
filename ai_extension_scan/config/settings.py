"""
Loads and saves user settings.
Persists to config/user_settings.json.

Fields:
  hotkey          str   default 'ctrl+shift+s'
  check_mode      str   'grammar' | 'spelling' | 'structure' | 'tone' | 'full'
  auto_start      bool  add to system startup
  save_history    bool  log results locally
  privacy_mode    bool  auto-delete temp screenshot after API call
  appearance_mode str   'light' | 'dark' | 'system'
  color_theme     str   'blue' | 'green' | 'dark-blue'

Note: AI provider and API key are stored separately in config/ai_provider.json.
"""

import json
import os

DEFAULTS = {
    "hotkey": "ctrl+shift+s",
    "check_mode": "full",
    "auto_start": False,
    "save_history": True,
    "privacy_mode": True,
    "appearance_mode": "system",
    "color_theme": "blue",
    "active_preset": "general",
    "max_concurrent_scans": 3,   # max panels open at once (1–10)
}

_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "user_settings.json")

# ── In-process cache (invalidated on every save()) ────────────────────────────
_cache: dict | None = None


def load() -> dict:
    """Return merged settings (defaults + saved overrides). Result is cached in-process."""
    global _cache
    if _cache is not None:
        return _cache.copy()

    settings = DEFAULTS.copy()
    if os.path.exists(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            settings.update(overrides)
        except (json.JSONDecodeError, OSError):
            pass

    _cache = settings
    return _cache.copy()


def save(settings: dict) -> None:
    """Write settings dict to config/user_settings.json and invalidate cache."""
    global _cache
    os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    _cache = None   # invalidate so next load() re-reads fresh values
