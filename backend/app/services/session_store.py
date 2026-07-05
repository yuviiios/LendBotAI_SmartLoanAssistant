import json
import os
import redis

# Redis-backed session store.
# Sessions survive server restarts and scale across multiple instances.
# Free Redis instance available on Render (25MB limit — sufficient for this project).
# REDIS_URL is set automatically by Render when you link a Redis instance.
# For local development, run Redis locally or use a free Redis Cloud instance
# and add REDIS_URL=redis://localhost:6379 to your backend .env file.

SESSION_TTL_SECONDS = 60 * 60 * 2  # sessions expire after 2 hours of inactivity


class SessionStore:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        self.client = redis.from_url(
            redis_url,
            decode_responses=True,   # return strings, not bytes
        )

    def get(self, session_id: str) -> dict:
        try:
            data = self.client.get(f"session:{session_id}")
            return json.loads(data) if data else {}
        except Exception as e:
            # If Redis is unreachable, return empty state — don't crash the app
            print(f"Redis GET Error: {e}")
            return {}

    def save(self, session_id: str, state: dict):
        try:
            self.client.setex(
                name=f"session:{session_id}",
                time=SESSION_TTL_SECONDS,   # auto-expire idle sessions
                value=json.dumps(state),
            )
        except Exception as e:
            # If Redis is unreachable, fail silently — state just won't persist
            print(f"Redis SAVE Error: {e}")