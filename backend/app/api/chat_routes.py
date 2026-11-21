from time import perf_counter
import asyncio
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logger import StructuredLogger
from app.dependencies import get_chat_agent, get_session_store
from app.services.applications import load_application
from app.services.session_store import TurnConflict

router = APIRouter()
logger = StructuredLogger("ChatTurns")


class ChatRequest(BaseModel):
    campaign: Literal["education", "travel", "personal loan"] | None = None
    session_id: str = Field(min_length=1, max_length=128)
    revision: int | None = Field(default=None, ge=0)
    message: str = Field(min_length=1, max_length=2000)


@router.post("/chat")
def chat(req: ChatRequest):
    started = perf_counter()
    sessions = get_session_store()
    try:
        row, owner = sessions.begin(req.session_id, req.revision)
        state = row["state"]
        if req.campaign and not state:
            state["campaign"] = req.campaign
        # Replaying a confirmed turn after a crash reopens the same application.
        state.setdefault("submission_key", str(uuid5(NAMESPACE_URL, f"{req.session_id}/{row['revision']}")))
        history = row["history"] + [{"role": "user", "content": req.message}]
        try:
            result = asyncio.run(get_chat_agent().handle_message(req.message, state, history))
        except Exception:
            sessions.finish(req.session_id, owner)
            raise
        history.append({"role": "assistant", "content": result["reply"]})
        revision = row["revision"] + 1
        sessions.finish(req.session_id, owner, state=result["state"], history=history[-50:], revision=revision)
        logger.info("chat_turn", stage=state.get("stage", "COLLECT_PAN"), campaign=state.get("campaign"),
                    elapsed_ms=round((perf_counter() - started) * 1000), revision=revision)
        return dict(result, revision=revision)
    except TurnConflict:
        raise HTTPException(409, "Another turn updated this chat. Refresh to see the latest reply.")


@router.get("/chat/history/{session_id}")
def get_chat_history(session_id: str):
    return {"session_id": session_id, "messages": get_session_store().snapshot(session_id)["history"]}


@router.get("/chat/{session_id}")
def restore_chat(session_id: str):
    row = get_session_store().snapshot(session_id)
    state, history = row["state"], row["history"]
    decision = state.get("decision", {})
    if state.get("application_id"):
        application = load_application(state["application_id"])
        if application and application["decision"]:
            latest = application["decision"]
            if latest != decision and latest.get("slip_digest"):
                reply = ("Your salary was verified and the sanction letter is ready." if latest["stage"] == "SANCTION"
                         else latest["result"]["reason"])
                history = history + [{"role": "assistant", "content": reply}]
            decision = latest
    return {"history": history, "decision": decision, "revision": row["revision"]}
