from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import get_chat_agent, get_session_store

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    sessions = get_session_store()
    chat_agent = get_chat_agent()

    state = sessions.get(req.session_id) or {}
    result = await chat_agent.handle_message(req.message, state)

    if "state" in result:
        sessions.save(req.session_id, result["state"])

    return result