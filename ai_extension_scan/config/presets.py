"""
Writing context presets.
Allows the user to select predefined or custom instructions to prepend to proofreading checks.
"""

import json
import os

DEFAULT_PRESETS = {
    "general": {
        "name": "🌟 General",
        "description": "Standard general-purpose proofreading constraints.",
        "rules": "Target: General writing. Verify standard grammar, spelling, and readability.",
        "is_custom": False
    },
    "professional": {
        "name": "💼 Professional",
        "description": "Clear, concise, and polite business writing.",
        "rules": "Target: Professional communication. Prioritize active voice, clarity, politeness, and conciseness. Avoid overly academic phrasing or casual fluff.",
        "is_custom": False
    },
    "academic": {
        "name": "🎓 Academic",
        "description": "Formal, objective, and precise syntax.",
        "rules": "Target: Academic publishing. Enforce objective tone, strict formal grammar rules, and complete vocabulary accuracy. Avoid contractions (like 'can't', 'don't') and colloquialisms.",
        "is_custom": False
    },
    "technical": {
        "name": "💻 Technical / Code",
        "description": "Preserves code elements and technical jargon.",
        "rules": "Target: Software documentation and development. DO NOT flag code elements, variable names (e.g. camelCase, snake_case, functions), API endpoints, CLI commands, or file paths as spelling or grammar errors. Keep the technical terms intact.",
        "is_custom": False
    },
    "casual": {
        "name": "💬 Casual Chat",
        "description": "Relaxed, friendly, and informal.",
        "rules": "Target: Friendly instant messaging. Allow contractions, casual slang, abbreviations (e.g. 'imo', 'btw'), and relaxed punctuation. Only flag spelling errors that hinder understanding.",
        "is_custom": False
    },
    "creative": {
        "name": "🎨 Creative",
        "description": "Expressive styling, tolerating creative license.",
        "rules": "Target: Narrative and prose. Allow poetic license, styling variance, fragments, and descriptive vocabulary. Focus corrections on structural flow and spelling mistakes, avoiding strict grammar enforcement.",
        "is_custom": False
    }
}

_CUSTOM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_presets.json")

# ── In-process cache ──────────────────────────────────────────────────────────
_custom_cache: dict | None = None
_merged_cache: dict | None = None


def _invalidate_cache() -> None:
    global _custom_cache, _merged_cache
    _custom_cache = None
    _merged_cache = None


def load_custom_presets() -> dict:
    """Load user-defined presets from config/custom_presets.json (cached)."""
    global _custom_cache
    if _custom_cache is not None:
        return _custom_cache
    if not os.path.exists(_CUSTOM_PATH):
        _custom_cache = {}
        return _custom_cache
    try:
        with open(_CUSTOM_PATH, "r", encoding="utf-8") as f:
            _custom_cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        _custom_cache = {}
    return _custom_cache


def save_custom_presets(custom: dict) -> None:
    """Save user-defined presets to config/custom_presets.json and invalidate cache."""
    _invalidate_cache()
    os.makedirs(os.path.dirname(_CUSTOM_PATH), exist_ok=True)
    with open(_CUSTOM_PATH, "w", encoding="utf-8") as f:
        json.dump(custom, f, indent=2, ensure_ascii=False)


def load_presets() -> dict:
    """Return all presets merged (defaults + custom). Result is cached in-process."""
    global _merged_cache
    if _merged_cache is not None:
        return _merged_cache
    presets = DEFAULT_PRESETS.copy()
    presets.update(load_custom_presets())
    _merged_cache = presets
    return _merged_cache


def save_custom_preset(preset_id: str, name: str, rules: str, description: str) -> None:
    """Create or update a custom preset."""
    custom = load_custom_presets()
    custom[preset_id] = {
        "name": name,
        "description": description,
        "rules": rules,
        "is_custom": True
    }
    save_custom_presets(custom)


def delete_custom_preset(preset_id: str) -> None:
    """Delete a custom preset by its ID."""
    custom = load_custom_presets()
    if preset_id in custom:
        del custom[preset_id]
        save_custom_presets(custom)
