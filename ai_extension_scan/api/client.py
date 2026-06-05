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
    """Write provider config to config/ai_provider.json and invalidate cached provider."""
    _invalidate_provider_cache()
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── Provider cache ─────────────────────────────────────────────────────────
# The SDK client (e.g. genai.Client) is expensive to construct on every scan.
# We keep one instance alive and only recreate it when the config changes.

_cached_provider: AIProvider | None = None
_cached_provider_key: tuple | None = None   # (provider_id, model, api_key)


def _invalidate_provider_cache() -> None:
    global _cached_provider, _cached_provider_key
    _cached_provider = None
    _cached_provider_key = None


# ── Factory ────────────────────────────────────────────────────────────────

def get_provider() -> AIProvider:
    """
    Read config/ai_provider.json and return the correct AIProvider instance.
    The instance is cached — a new one is only created when the config changes.
    Raises ValueError for unknown provider names.
    Raises ImportError if the required SDK is not installed.
    """
    global _cached_provider, _cached_provider_key

    cfg         = load_provider_config()
    provider_id = cfg.get("provider", "gemini").lower().strip()
    model       = cfg.get("model", "")
    api_key     = cfg.get("api_key", "")
    cache_key   = (provider_id, model, api_key)

    if _cached_provider is not None and _cached_provider_key == cache_key:
        return _cached_provider

    # Build a fresh provider
    if provider_id == "gemini":
        from api.providers.gemini import GeminiProvider
        provider = GeminiProvider(cfg)

    elif provider_id == "openai":
        from api.providers.openai import OpenAIProvider
        provider = OpenAIProvider(cfg)

    elif provider_id == "anthropic":
        from api.providers.anthropic import AnthropicProvider
        provider = AnthropicProvider(cfg)

    else:
        supported = ", ".join(PROVIDER_DISPLAY_NAMES.keys())
        raise ValueError(
            f"Unknown AI provider '{provider_id}' in config/ai_provider.json. "
            f"Supported values: {supported}"
        )

    _cached_provider     = provider
    _cached_provider_key = cache_key
    return _cached_provider
