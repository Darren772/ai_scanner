"""
Factory module — reads config/ai_provider.json and returns the correct AIProvider.

Usage (anywhere in the app):
    from api.client import get_provider
    provider = get_provider()
    raw     = provider.send(image_path, prompt)
    parsed  = provider.parse_response(raw)

Supported providers:  gemini | openai | anthropic
"""

import json
import os

from api.base import AIProvider

# ── Config file location ───────────────────────────────────────────────────
_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "ai_provider.json",
)

_DEFAULTS: dict = {
    "provider": "gemini",
    "model":    "gemini-2.0-flash",
    "api_key":  "",
}

# Human-readable names for the UI
PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "gemini":    "Google Gemini",
    "openai":    "OpenAI GPT",
    "anthropic": "Anthropic Claude",
}

# Default model for each provider (shown in UI when user switches)
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "gemini":    "gemini-2.0-flash",
    "openai":    "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
}


# ── Config I/O ─────────────────────────────────────────────────────────────

def load_provider_config() -> dict:
    """Return merged provider config (defaults + saved values)."""
    if not os.path.exists(_CONFIG_PATH):
        save_provider_config(_DEFAULTS.copy())
        return _DEFAULTS.copy()
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return {**_DEFAULTS, **saved}
    except (json.JSONDecodeError, OSError):
        return _DEFAULTS.copy()


def save_provider_config(cfg: dict) -> None:
    """Write provider config to config/ai_provider.json."""
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── Factory ────────────────────────────────────────────────────────────────

def get_provider() -> AIProvider:
    """
    Read config/ai_provider.json and return the correct AIProvider instance.
    Raises ValueError for unknown provider names.
    Raises ImportError if the required SDK is not installed.
    """
    cfg = load_provider_config()
    provider_id = cfg.get("provider", "gemini").lower().strip()

    if provider_id == "gemini":
        from api.providers.gemini import GeminiProvider
        return GeminiProvider(cfg)

    elif provider_id == "openai":
        from api.providers.openai import OpenAIProvider
        return OpenAIProvider(cfg)

    elif provider_id == "anthropic":
        from api.providers.anthropic import AnthropicProvider
        return AnthropicProvider(cfg)

    else:
        supported = ", ".join(PROVIDER_DISPLAY_NAMES.keys())
        raise ValueError(
            f"Unknown AI provider '{provider_id}' in config/ai_provider.json. "
            f"Supported values: {supported}"
        )
