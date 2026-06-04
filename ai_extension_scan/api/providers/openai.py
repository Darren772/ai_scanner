"""
OpenAI GPT-4o Vision provider implementation.
Requires: pip install openai

Supported models: gpt-4o, gpt-4o-mini, gpt-4-turbo
"""

import base64
from api.base import AIProvider


class OpenAIProvider(AIProvider):

    def __init__(self, config: dict) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "The 'openai' package is not installed.\n"
                "Run:  pip install openai"
            )
        self._model = config.get("model", "gpt-4o")
        self._client = OpenAI(api_key=config.get("api_key", ""))

    def send(self, image_path: str, prompt: str) -> str:
        """Send image (optional) + prompt to OpenAI Vision. Returns raw response text."""
        content = [{"type": "text", "text": prompt}]
        
        if image_path:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}",
                    "detail": "high",
                },
            })

        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )
        return response.choices[0].message.content
