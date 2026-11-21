from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.agents.chat_agent import ChatAgent
from app.dependencies import get_master_agent
from app.main import app
from app.services.customer_directory import customers_by_pan


def test_mock_systems_share_customer_ids():
    client = TestClient(app)
    records = customers_by_pan()
    assert len({c.customer_id for c in records.values()}) >= 10
    for customer in records.values():
        for system, field in [("offers", "preapproved_limit"), ("crm", "address"), ("bureau", "credit_score")]:
            payload = client.get(f"/api/mock/{system}/{customer.pan}").json()
            assert payload["customer_id"] == customer.customer_id
            assert payload[field] == getattr(customer, field)
    for system in ["offers", "crm", "bureau"]:
        assert client.get(f"/api/mock/{system}/ZZZZZ1234Z").status_code == 404


def test_claimed_income_and_client_flag_cannot_skip_required_evidence():
    response = TestClient(app).post("/api/apply-loan", json={
        "pan": "ABCDE1234F", "monthly_income": 999999, "loan_amount": 300000,
        "tenure_months": 24, "is_preapproved": True, "verified_monthly_salary": 999999,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "PENDING"
    assert result["data"]["reason_code"] == "SALARY_SLIP_REQUIRED"


@pytest.mark.asyncio
async def test_chat_waits_for_evidence_instead_of_closing():
    chat = ChatAgent(get_master_agent(), Mock())
    state = {"stage": "HUMAN_REVIEW", "pan": "ABCDE1234F", "monthly_income": 999999,
             "loan_amount": 300000, "tenure_months": 24}
    result = await chat.handle_message("yes", state)
    assert result["state"]["stage"] == "AWAITING_SALARY_SLIP"
    assert result["decision"]["result"]["reason_code"] == "SALARY_SLIP_REQUIRED"
    assert "sanction_letter_url" not in result
