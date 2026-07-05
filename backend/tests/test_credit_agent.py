import pytest

from app.agents.credit_agent import CreditAgent
from app.services.credit_score_service import CreditScoreService


@pytest.mark.asyncio
async def test_auto_approve_high_score():
    """
    Credit score >= 750
    EMI within limits
    All documents present
    """
    agent = CreditAgent(CreditScoreService())

    score = await agent.fetch_credit_score("ABCDE1234F")

    result = agent.evaluate_eligibility(
        score=score,
        loan_amount=100000,
        monthly_income=60000,
        tenure=24,
        is_preapproved=False,
        documents={
            "payslip": True,
            "kyc_verified": True,
        },
    )

    assert result["status"] == "AUTO_APPROVE"


@pytest.mark.asyncio
async def test_conditional_approve_missing_payslip():
    """
    Credit score between 700-749 → CONDITIONAL_APPROVE path.
    Missing payslip → HOLD.

    FIX: original used loan_amount=150000 with monthly_income=50000.
    After the evaluation order fix in credit_agent.py, the income cap
    check (loan > 2x income) now runs BEFORE the document check.
    150000 > 50000*2 (100000) → income cap triggered → REJECT returned
    before the doc check ever runs, so HOLD was never reached.

    Fix: loan_amount=80000 which is within 2x income (50000*2=100000).
    Now the income cap passes, EMI check passes, and the missing
    payslip doc check correctly returns HOLD.
    """
    agent = CreditAgent(CreditScoreService())

    score = await agent.fetch_credit_score("PQRSX9999Z")  # score = 720

    result = agent.evaluate_eligibility(
        score=score,
        loan_amount=80000,      # FIX: was 150000 — exceeded 2x income (100000)
        monthly_income=50000,   # 2x income = 100000, so 80000 is within limit
        tenure=24,
        is_preapproved=False,
        documents={
            "payslip": False,   # missing payslip triggers HOLD
            "kyc_verified": True,
        },
    )

    assert result["status"] == "HOLD"
    assert "payslip" in result["missing_documents"]


@pytest.mark.asyncio
async def test_reject_low_credit_score():
    """
    Credit score < 700 → REJECT
    """
    agent = CreditAgent(CreditScoreService())

    score = await agent.fetch_credit_score("LOWSC0000X")  # score = 650

    result = agent.evaluate_eligibility(
        score=score,
        loan_amount=100000,
        monthly_income=50000,
        tenure=24,
        is_preapproved=False,
        documents={
            "payslip": True,
            "kyc_verified": True,
        },
    )

    assert result["status"] == "REJECT"


@pytest.mark.asyncio
async def test_reject_high_emi():
    """
    EMI > 50% of salary → REJECT.
    loan=1000000 at 14% over 24 months → EMI ≈ 48,013
    which is > 50% of income 30,000 (15,000 limit).
    """
    agent = CreditAgent(CreditScoreService())

    score = await agent.fetch_credit_score("ABCDE1234F")  # score = 780

    result = agent.evaluate_eligibility(
        score=score,
        loan_amount=1000000,
        monthly_income=30000,
        tenure=24,
        is_preapproved=False,
        documents={
            "payslip": True,
            "kyc_verified": True,
        },
    )

    assert result["status"] == "REJECT"