"""
Orchestrates a full check run:
  1. Takes image_path + check mode
  2. Picks the right prompt from config/prompts.py
  3. Gets the configured AI provider via api/client.py
  4. Sends image + prompt, parses response into a CheckResult
  5. Optionally saves to history/log.py
"""

from dataclasses import dataclass, field


@dataclass
class CheckResult:
    grammar:   list[str] = field(default_factory=list)   # list of grammar issues
    spelling:  list[str] = field(default_factory=list)   # list of spelling errors
    structure: list[str] = field(default_factory=list)   # structure/flow suggestions
    tone:      list[str] = field(default_factory=list)   # tone observations
    rewrite:   str = ""                                   # full corrected version
    raw:       str = ""                                   # raw API response (for debugging)


_PROMPT_MAP = {
    "full":      "full_check",
    "grammar":   "grammar_only",
    "spelling":  "spelling_only",
    "structure": "structure_only",
    "tone":      "tone_only",
}


def run(image_path: str, mode: str) -> CheckResult:
    """Run check and return structured result."""
    from config import prompts
    from config import presets as _presets_mod
    from config import settings as _settings_mod
    from api.client import get_provider   # ← provider-agnostic

    # 1. Load settings once — used for preset selection AND save_history below
    _settings = _settings_mod.load()

    # 2. Load the active preset so it can fully control the prompt.
    try:
        active_preset_id = _settings.get("active_preset", "general")
        all_presets  = _presets_mod.load_presets()
        active_preset = all_presets.get(active_preset_id, all_presets.get("general", {}))
        rules    = active_preset.get("rules", "").strip()
        is_custom = active_preset.get("is_custom", False)
    except Exception:
        rules     = ""
        is_custom = False

    # 3. Build the prompt.
    # Always start with the mode-specific base prompt so the correct output
    # structure (e.g. grammar-only) and section headers are in place.
    prompt_fn_name = _PROMPT_MAP.get(mode, "full_check")
    prompt = getattr(prompts, prompt_fn_name)()

    # If there are rules (from any preset — built-in or custom), inject them
    # right after the first line (the AI's role instruction) as a clearly
    # labelled constraint block. The mode-specific formatting instructions
    # that follow immediately make it unambiguous that those come first.
    if rules:
        lines = prompt.split("\n")
        constraint_block = (
            f"\n[CUSTOM WRITING RULES — APPLY THESE TO YOUR OUTPUT]\n"
            f"{rules}\n"
            f"[END OF CUSTOM RULES]\n"
            f"The above rules take priority over your default style, but you MUST still use "
            f"the section headers and output format defined below exactly as written.\n"
        )
        prompt = lines[0] + constraint_block + "\n".join(lines[1:])

    # 4. Get cached provider and call it
    provider = get_provider()
    raw = provider.send(image_path, prompt)

    # 5. Parse using the provider's shared parser
    parsed = provider.parse_response(raw)

    result = CheckResult(
        grammar=parsed["grammar"],
        spelling=parsed["spelling"],
        structure=parsed["structure"],
        tone=parsed["tone"],
        rewrite=parsed["rewrite"],
        raw=raw,
    )

    # 6. Save history if enabled (reuse already-loaded settings — no second disk read)
    try:
        if _settings.get("save_history", True):
            from history import log as history_log
            history_log.append(mode, result)
    except Exception:
        pass  # Never let logging failure break the main flow

    return result

