import pytest

from app.agents.master_agent import MasterAgent
from app.agents.sales_agent import SalesAgent
from app.agents.kyc_agent import KycAgent
from app.agents.credit_agent import CreditAgent
from app.agents.sanction_agent import SanctionAgent


# -----------------------------
# Mock Services
# -----------------------------
class MockCRMService:
    def fetch_kyc(self, pan: str):
        return {
            "kyc_verified": True,
            "documents": {
                "payslip": True,
                "aadhaar": True,
            }
        }


class MockCreditScoreService:
    async def get_score(self, pan: str) -> int:
        return 780  # High score for approval


# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def master_agent():
    sales_agent = SalesAgent()
    kyc_agent = KycAgent(MockCRMService())
    credit_agent = CreditAgent(MockCreditScoreService())
    sanction_agent = SanctionAgent()

    return MasterAgent(
        sales_agent=sales_agent,
        kyc_agent=kyc_agent,
        credit_agent=credit_agent,
        sanction_agent=sanction_agent,
    )


# -----------------------------
# Tests
# -----------------------------
@pytest.mark.asyncio
async def test_end_to_end_auto_approved_flow(master_agent):
    """
    Full happy-path flow:
    Sales → KYC → Credit → Sanction
    """

    result = await master_agent.process_loan_application(
        pan="ABCDE1234F",
        loan_amount=100000,
        tenure_months=24,
        monthly_income=60000,
        is_preapproved=False,
    )

    assert result["stage"] == "SANCTION"
    assert result["result"]["status"] == "SANCTIONED"
    assert "sanction_id" in result["result"]


@pytest.mark.asyncio
async def test_flow_stops_on_kyc_failure():
    """
    Flow should stop at KYC stage if KYC fails.
    """

    class FailedKYCService:
        def fetch_kyc(self, pan: str):
            return {"kyc_verified": False, "documents": {}}

    master_agent = MasterAgent(
        sales_agent=SalesAgent(),
        kyc_agent=KycAgent(FailedKYCService()),
        credit_agent=CreditAgent(MockCreditScoreService()),
        sanction_agent=SanctionAgent(),
    )

    result = await master_agent.process_loan_application(
        pan="BADKYC9999",
        loan_amount=100000,
        tenure_months=24,
        monthly_income=60000,
    )

    assert result["stage"] == "KYC"
    assert result["result"]["status"] == "FAILED"


@pytest.mark.asyncio
async def test_flow_stops_on_credit_rejection():
    """
    Flow should stop at Credit stage if credit rejects.
    """

    class LowScoreService:
        async def get_score(self, pan: str) -> int:
            return 650  # Low score → reject

    master_agent = MasterAgent(
        sales_agent=SalesAgent(),
        kyc_agent=KycAgent(MockCRMService()),
        credit_agent=CreditAgent(LowScoreService()),
        sanction_agent=SanctionAgent(),
    )

    result = await master_agent.process_loan_application(
        pan="LOWCREDIT1",
        loan_amount=100000,
        tenure_months=24,
        monthly_income=60000,
    )

    assert result["stage"] == "CREDIT"
    assert result["result"]["status"] == "REJECT"
