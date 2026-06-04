"""
Gemini Vision provider implementation.
Uses the new google-genai SDK (replaces the deprecated google-generativeai).
"""

from api.base import AIProvider
from google import genai
from PIL import Image


class GeminiProvider(AIProvider):

    def __init__(self, config: dict) -> None:
        api_key = config.get("api_key", "")
        self._model_name = config.get("model", "gemini-2.0-flash")
        self._client = genai.Client(api_key=api_key)

    def send(self, image_path: str, prompt: str) -> str:
        """Send image (optional) + prompt to Gemini. Returns raw response text."""
        contents = [prompt]
        if image_path:
            image = Image.open(image_path)
            contents.append(image)
            
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=contents,
        )
        return response.text
