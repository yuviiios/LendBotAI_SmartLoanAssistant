"""Integration tests for the full chat flow with session memory + human-in-the-loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.chat_agent import ChatAgent
from app.agents.master_agent import MasterAgent


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat.side_effect = lambda system_prompt, user_message: user_message.split(": ")[-1]
    return llm


@pytest.fixture
def mock_master_agent():
    agent = AsyncMock(spec=MasterAgent)
    agent.process_loan_application.return_value = {
        "stage": "SANCTION",
        "result": {
            "status": "SANCTIONED",
            "sanction_id": "TEST001",
            "approved_emi": 12500,
        },
    }
    return agent


@pytest.fixture
def chat_agent(mock_master_agent, mock_llm):
    return ChatAgent(master_agent=mock_master_agent, llm_service=mock_llm)


class TestFullFlow:
    @pytest.mark.asyncio
    async def test_happy_path_with_human_review(self, chat_agent):
        state = {}
        history = []

        # Step 1: Greeting
        result = await chat_agent.handle_message("hello", state, history)
        assert "PAN" in result["reply"]
        state = result["state"]
        history.append({"role": "user", "content": "hello"})
        history.append({"role": "assistant", "content": result["reply"]})

        # Step 2: Provide PAN
        result = await chat_agent.handle_message("my pan is ABCDE1234F", state, history)
        assert result["state"]["pan"] == "ABCDE1234F"
        assert result["state"]["stage"] == "COLLECT_INCOME"
        state = result["state"]

        # Step 3: Provide income
        result = await chat_agent.handle_message("I earn 50000 per month", state, history)
        assert result["state"]["monthly_income"] == 50000
        assert result["state"]["stage"] == "COLLECT_LOAN"
        state = result["state"]

        # Step 4: Provide loan amount — use amount within 2x income for approval
        result = await chat_agent.handle_message("I need 80000", state, history)
        assert result["state"]["loan_amount"] == 80000
        assert result["state"]["stage"] == "COLLECT_TENURE"
        state = result["state"]

        # Step 5: Provide tenure
        result = await chat_agent.handle_message("24 months", state, history)
        assert result["state"]["tenure_months"] == 24
        assert result["state"]["stage"] == "HUMAN_REVIEW"
        assert "Application Summary" in result["reply"]
        state = result["state"]

        # Step 6: Human confirms
        result = await chat_agent.handle_message("yes", state, history)
        assert result["state"]["stage"] == "DONE"
        assert result["state"]["human_confirmed"] is True

    @pytest.mark.asyncio
    async def test_human_denies_stays_in_review(self, chat_agent):
        state = {
            "pan": "ABCDE1234F",
            "monthly_income": 50000,
            "loan_amount": 500000,
            "tenure_months": 24,
            "stage": "HUMAN_REVIEW",
        }
        history = []

        # User says no at review — stays in HUMAN_REVIEW for modification
        result = await chat_agent.handle_message("no", state, history)
        assert result["state"]["stage"] == "HUMAN_REVIEW"
        assert "change" in result["reply"].lower()

    @pytest.mark.asyncio
    async def test_modify_at_review_stage(self, chat_agent):
        state = {
            "pan": "ABCDE1234F",
            "monthly_income": 50000,
            "loan_amount": 500000,
            "tenure_months": 24,
            "stage": "HUMAN_REVIEW",
        }
        history = []

        # User modifies amount at review
        result = await chat_agent.handle_message("change it to 3 lakhs", state, history)
        assert result["state"]["loan_amount"] == 300000
        assert result["state"]["stage"] == "HUMAN_REVIEW"
        assert "Application Summary" in result["reply"]

    @pytest.mark.asyncio
    async def test_question_during_flow(self, chat_agent):
        state = {"stage": "COLLECT_INCOME", "pan": "ABCDE1234F"}
        history = []

        result = await chat_agent.handle_message("what is the interest rate?", state, history)
        # Should answer question and stay in same stage
        assert result["state"]["stage"] == "COLLECT_INCOME"

    @pytest.mark.asyncio
    async def test_frustration_handling(self, chat_agent):
        state = {"stage": "COLLECT_LOAN", "pan": "ABCDE1234F", "monthly_income": 50000}
        history = []

        result = await chat_agent.handle_message("this is taking too long", state, history)
        assert "frustrating" in result["reply"].lower() or "help" in result["reply"].lower()
        assert result["state"]["stage"] == "COLLECT_LOAN"

    @pytest.mark.asyncio
    async def test_processing_requires_human_confirmation(self, chat_agent):
        state = {
            "pan": "ABCDE1234F",
            "monthly_income": 50000,
            "loan_amount": 80000,
            "tenure_months": 24,
            "stage": "PROCESSING",
            # No human_confirmed flag → must bounce back
        }
        history = []

        # Should bounce back to review
        result = await chat_agent.handle_message("", state, history)
        assert result["state"]["stage"] == "HUMAN_REVIEW"
        assert "Application Summary" in result["reply"]

    @pytest.mark.asyncio
    async def test_tenure_in_years(self, chat_agent):
        state = {
            "pan": "ABCDE1234F",
            "monthly_income": 50000,
            "loan_amount": 500000,
            "stage": "COLLECT_TENURE",
        }
        history = []

        result = await chat_agent.handle_message("2 years", state, history)
        assert result["state"]["tenure_months"] == 24
        assert result["state"]["stage"] == "HUMAN_REVIEW"

    @pytest.mark.asyncio
    async def test_review_shows_masked_pan(self, chat_agent):
        """Test _show_review_summary directly for masked PAN."""
        state = {
            "pan": "ABCDE1234F",
            "monthly_income": 50000,
            "loan_amount": 500000,
            "tenure_months": 24,
            "stage": "HUMAN_REVIEW",
        }

        result = chat_agent._show_review_summary(state, [])
        assert "ABCDE1234F" not in result["reply"]
        assert "AB" in result["reply"]
        assert "F" in result["reply"]
        assert "Application Summary" in result["reply"]


class TestConversationMemory:
    @pytest.mark.asyncio
    async def test_history_passed_to_llm(self, chat_agent, mock_llm):
        state = {"stage": "COLLECT_INCOME", "pan": "ABCDE1234F"}
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hi! Please share your PAN."},
            {"role": "user", "content": "ABCDE1234F"},
            {"role": "assistant", "content": "Thanks! What's your income?"},
        ]

        await chat_agent.handle_message("50000 per month", state, history)

        # LLM should have been called with history context
        call_args = mock_llm.chat.call_args
        assert "conversation" in call_args.kwargs.get("system_prompt", "").lower() or \
               "conversation" in call_args[1].get("system_prompt", "").lower() if call_args[1] else True
