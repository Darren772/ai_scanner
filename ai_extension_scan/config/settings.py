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
}

_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "user_settings.json")


def load() -> dict:
    """Return merged settings (defaults + saved overrides from user_settings.json)."""
    settings = DEFAULTS.copy()
    if os.path.exists(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            settings.update(overrides)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save(settings: dict) -> None:
    """Write settings dict to config/user_settings.json."""
    os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
