"""
app/dependencies.py

Single source of truth for all agent and service construction.
Both chat_routes and loan_routes import from here via FastAPI Depends().

Previously, each router built its own agent tree independently —
chat_routes at module level, loan_routes per-request. This caused:
  - Duplicate instantiation
  - Risk of the two trees diverging when services gain real state
"""
import os
from functools import lru_cache

from app.agents.master_agent import MasterAgent
from app.agents.sales_agent import SalesAgent
from app.agents.kyc_agent import KycAgent
from app.agents.credit_agent import CreditAgent
from app.agents.sanction_agent import SanctionAgent
from app.agents.chat_agent import ChatAgent
from app.services.crm_service import CRMService
from app.services.credit_score_service import CreditScoreService
from app.services.llm_service import LLMService
from app.services.session_store import SessionStore


@lru_cache(maxsize=1)
def get_master_agent() -> MasterAgent:
    """Singleton MasterAgent — built once, reused across all requests."""
    return MasterAgent(
        sales_agent=SalesAgent(),
        kyc_agent=KycAgent(CRMService()),
        credit_agent=CreditAgent(CreditScoreService()),
        sanction_agent=SanctionAgent(),
    )


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService(api_key=os.getenv("GEMINI_API_KEY"))


@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    return SessionStore()


@lru_cache(maxsize=1)
def get_chat_agent() -> ChatAgent:
    return ChatAgent(
        master_agent=get_master_agent(),
        llm_service=get_llm_service(),
    )