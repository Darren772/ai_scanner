"""
Anthropic Claude Vision provider implementation.
Requires: pip install anthropic

Supported models: claude-3-5-sonnet-20241022, claude-3-opus-20240229, claude-3-haiku-20240307
"""

import base64
from api.base import AIProvider


class AnthropicProvider(AIProvider):

    def __init__(self, config: dict) -> None:
        try:
            import anthropic as _anthropic
            self._anthropic = _anthropic
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is not installed.\n"
                "Run:  pip install anthropic"
            )
        self._model = config.get("model", "claude-3-5-sonnet-20241022")
        self._client = _anthropic.Anthropic(api_key=config.get("api_key", ""))

    def send(self, image_path: str, prompt: str) -> str:
        """Send image (optional) + prompt to Claude. Returns raw response text."""
        content = []
        if image_path:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            })
            
        content.append({
            "type": "text",
            "text": prompt,
        })

        message = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )
        return message.content[0].text
