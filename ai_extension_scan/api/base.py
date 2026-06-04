"""
Abstract base class for all AI providers.

Every provider (Gemini, OpenAI, Anthropic, ...) must subclass AIProvider
and implement send(). parse_response() is shared across all providers because
all prompts use the same ## SECTION header format.
"""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base interface every AI provider must implement."""

    @abstractmethod
    def send(self, image_path: str, prompt: str) -> str:
        """
        Send an image + prompt to the AI.
        Returns the raw text response.
        """
        ...

    # ── Shared parser ──────────────────────────────────────────────────────
    # parse_response() is NOT abstract — it's identical for all providers
    # because config/prompts.py always uses the same ## SECTION format.

    def parse_response(self, raw: str) -> dict:
        """
        Parse raw AI response into a structured dict:
        {
          'grammar':   ['issue 1', ...],
          'spelling':  [...],
          'structure': [...],
          'tone':      [...],
          'rewrite':   'full corrected text'
        }
        Splits by ## GRAMMAR / ## SPELLING / ## STRUCTURE / ## TONE / ## REWRITE.
        """
        sections: dict = {
            "grammar":   [],
            "spelling":  [],
            "structure": [],
            "tone":      [],
            "rewrite":   "",
        }

        _HEADER_MAP = {
            "GRAMMAR":   "grammar",
            "SPELLING":  "spelling",
            "STRUCTURE": "structure",
            "TONE":      "tone",
            "REWRITE":   "rewrite",
        }

        current: str | None = None
        rewrite_lines: list[str] = []

        for line in raw.splitlines():
            stripped = line.strip()
            
            # Make parsing highly resilient to markdown formatting (e.g. "**## GRAMMAR:**")
            clean_header = stripped.strip("#*: ").upper()
            matched = _HEADER_MAP.get(clean_header)
            
            if matched:
                current = matched
                continue

            if not stripped:
                if current == "rewrite" and rewrite_lines:
                    rewrite_lines.append("")
                continue

            if current in ("grammar", "spelling", "structure", "tone"):
                text = stripped.lstrip("-• ").strip()
                if text and text.lower() != "none found.":
                    sections[current].append(text)
            elif current == "rewrite":
                rewrite_lines.append(stripped)

        sections["rewrite"] = "\n".join(rewrite_lines).strip()
        return sections
