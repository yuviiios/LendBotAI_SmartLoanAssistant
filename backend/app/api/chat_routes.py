from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import get_chat_agent, get_session_store

router = APIRouter()


class ChatRequest(BaseModel):
    campaign: Literal["education", "travel", "personal loan"] | None = None
    session_id: str
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    sessions = get_session_store()
    chat_agent = get_chat_agent()

    state = sessions.get(req.session_id) or {}

    if req.campaign and not state:
        state["campaign"] = req.campaign

    # Store user message in conversation history
    sessions.append_message(req.session_id, "user", req.message)

    # Pass conversation history to agent for context-aware responses
    conversation_history = sessions.get_history(req.session_id)
    result = await chat_agent.handle_message(req.message, state, conversation_history)

    if "state" in result:
        sessions.save(req.session_id, result["state"])

    # Store bot reply in conversation history
    if "reply" in result:
        sessions.append_message(req.session_id, "assistant", result["reply"])

    return result


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    sessions = get_session_store()
    history = sessions.get_history(session_id)
    return {"session_id": session_id, "messages": history}

@router.get("/chat/{session_id}")
def restore_chat(session_id: str):
    sessions = get_session_store()
    state = sessions.get(session_id)
    decision = state.get("decision", {})
    if state.get("application_id"):
        from app.services.applications import load_application
        row = load_application(state["application_id"])
        if row and row["decision"]:
            decision = row["decision"]
    return {"history": sessions.get_history(session_id), "decision": decision}
