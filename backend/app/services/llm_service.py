from google import genai
from google.genai import types


class LLMService:
    def __init__(self, api_key: str | None):
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=6000)) if api_key else None

    def chat(self, system_prompt: str, user_message: str) -> str:
        if self.client is None:
            raise RuntimeError("Conversation model unavailable")
        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite", contents=user_message,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        return response.text.strip()
