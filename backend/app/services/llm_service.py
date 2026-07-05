from google import genai
import traceback

class LLMService:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def chat(self, system_prompt: str, user_message: str) -> str:
        try:
            prompt = f"System: {system_prompt}\nUser: {user_message}"

            response = self.client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )

            return response.text.strip()

        except Exception as e:
            traceback.print_exc()
            return f"LLM Error: {str(e)}"