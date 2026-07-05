import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# FIX: build absolute path to app/static/outputs/ based on this file's
# location — works regardless of where pytest is run from.
#
# __file__  = .../backend/tests/test_api_apply_loan.py
# [0] dirname  = .../backend/tests/
# [1] dirname  = .../backend/
# then join    = .../backend/app/static/outputs/
#
# The old code used os.makedirs("app/static/outputs") which is a relative
# path — it resolves based on whatever the current working directory is
# when pytest runs, which may not be backend/. This caused FileNotFoundError
# because the directory was created in the wrong place.
STATIC_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "app", "static", "outputs"
)


def test_apply_loan_happy_path():
    """
    Full happy path end-to-end through the real API.
    PAN ABCDE1234F → score 780 → KYC verified → all docs present
    → AUTO_APPROVE → SANCTIONED.
    """
    os.makedirs(STATIC_OUTPUT_DIR, exist_ok=True)

    payload = {
        "pan": "ABCDE1234F",
        "loan_amount": 100000,
        "tenure_months": 24,
        "monthly_income": 60000,
        "is_preapproved": False,
    }

    response = client.post("/api/apply-loan", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "SUCCESS"
    assert data["stage"] == "SANCTION"
    assert data["data"]["status"] == "SANCTIONED"
    assert "sanction_id" in data["data"]
    assert data["data"]["approved_emi"] is not None
    assert data["data"]["terms"]["tenure_months"] == 24


def test_apply_loan_kyc_failure():
    """
    Unknown PAN → CRMService returns kyc_verified: False → KYC FAILED.
    """
    payload = {
        "pan": "BADKY00000",
        "loan_amount": 100000,
        "tenure_months": 24,
        "monthly_income": 60000,
        "is_preapproved": False,
    }

    response = client.post("/api/apply-loan", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "FAILURE"
    assert data["stage"] == "KYC"
    assert data["error"]["code"] in ["FAILED", "INCOMPLETE"]
    assert data["error"]["message"] is not None


def test_apply_loan_low_credit_score():
    """
    PAN LOWSC0000X → score 650 → KYC passes → credit REJECT.
    """
    os.makedirs(STATIC_OUTPUT_DIR, exist_ok=True)

    payload = {
        "pan": "LOWSC0000X",
        "loan_amount": 100000,
        "tenure_months": 24,
        "monthly_income": 60000,
        "is_preapproved": False,
    }

    response = client.post("/api/apply-loan", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "FAILURE"
    assert data["stage"] == "CREDIT"
    assert data["error"]["code"] == "REJECT"


def test_apply_loan_invalid_amount():
    """
    Loan amount of 5,000,000 exceeds max product limit of 2,000,000
    → SalesAgent rejects before KYC or credit runs.
    """
    payload = {
        "pan": "ABCDE1234F",
        "loan_amount": 5000000,
        "tenure_months": 24,
        "monthly_income": 60000,
        "is_preapproved": False,
    }

    response = client.post("/api/apply-loan", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "FAILURE"
    assert data["stage"] == "SALES"
    assert data["error"]["code"] == "REJECT"