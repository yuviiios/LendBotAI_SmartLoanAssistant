from decimal import Decimal

import pytest

from app.agents.credit_agent import CreditAgent


@pytest.mark.parametrize("score,amount,expected", [
    (699, 200000, "LOW_SCORE"),
    (700, 200000, "WITHIN_OFFER"),
    (700, 200001, "SALARY_SLIP_REQUIRED"),
    (800, 400000, "SALARY_SLIP_REQUIRED"),
    (800, 400001, "ABOVE_MAXIMUM"),
])
def test_offer_policy_boundaries(score, amount, expected):
    decision = CreditAgent(None).evaluate_eligibility(
        score=score, loan_amount=amount, tenure=24, preapproved_limit=200000,
    )
    assert decision["policy_version"] == "offer-v1"
    assert decision["reason_code"] == expected


@pytest.mark.parametrize("salary_delta,expected", [(0, "SALARY_VERIFIED"), (-0.01, "EMI_TOO_HIGH")])
def test_verified_salary_boundary(salary_delta, expected):
    agent = CreditAgent(None)
    emi = Decimal(str(agent.calculate_emi(300000, 14, 24)))
    decision = agent.evaluate_eligibility(
        score=700, loan_amount=300000, tenure=24, preapproved_limit=200000,
        verified_monthly_salary=float(2 * emi + Decimal(str(salary_delta))),
    )
    assert decision["reason_code"] == expected
