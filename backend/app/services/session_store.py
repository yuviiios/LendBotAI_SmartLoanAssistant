import json
import os
import redis
from typing import Any

SESSION_TTL_SECONDS = 60 * 60 * 2  # 2 hours


class SessionStore:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        self.client = redis.from_url(
            redis_url,
            decode_responses=True,
        )

    def get(self, session_id: str) -> dict:
        try:
            data = self.client.get(f"session:{session_id}")
            return json.loads(data) if data else {}
        except Exception as e:
            print(f"Redis GET Error: {e}")
            return {}

    def save(self, session_id: str, state: dict):
        try:
            self.client.setex(
                name=f"session:{session_id}",
                time=SESSION_TTL_SECONDS,
                value=json.dumps(state),
            )
        except Exception as e:
            print(f"Redis SAVE Error: {e}")

    # ----- Conversation Memory -----

    def get_history(self, session_id: str) -> list[dict]:
        try:
            data = self.client.get(f"history:{session_id}")
            return json.loads(data) if data else []
        except Exception as e:
            print(f"Redis GET history Error: {e}")
            return []

    def append_message(self, session_id: str, role: str, content: str):
        try:
            history = self.get_history(session_id)
            history.append({"role": role, "content": content})
            # Keep last 50 messages to avoid bloating Redis
            if len(history) > 50:
                history = history[-50:]
            self.client.setex(
                name=f"history:{session_id}",
                time=SESSION_TTL_SECONDS,
                value=json.dumps(history),
            )
        except Exception as e:
            print(f"Redis SAVE history Error: {e}")

    def get_summary_context(self, session_id: str, last_n: int = 10) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""
        recent = history[-last_n:]
        lines = []
        for msg in recent:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)
