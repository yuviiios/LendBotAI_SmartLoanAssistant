from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize("score,amount,status", [
    (700, 100000, "SANCTIONED"), (750, 180000, "HOLD"), (699, 100000, "REJECT"),
])
def test_custom_customer_journey(score, amount, status):
    client = TestClient(app)
    session = str(uuid4())
    profile = dict(name="Sample Applicant", phone="0000000012", address="12 Sample Road",
                   monthly_salary=65000, credit_score=score, preapproved_limit=100000)
    messages = ["Start custom simulation", str(amount), "24 months", "yes",
                "0000000000", profile["address"], profile["phone"], profile["address"]]
    for revision, message in enumerate(messages):
        body = dict(session_id=session, revision=revision, message=message)
        if revision == 0:
            body["profile"] = profile
        response = client.post("/api/chat", json=body)
        assert response.status_code == 200, response.text
        if revision == 5:
            assert response.json()["state"]["stage"] == "COLLECT_PHONE"

    decision = client.get("/api/chat/" + session).json()["decision"]
    assert decision["result"]["status"] == status
    if status == "HOLD":
        slip = client.get(decision["sample_slip_url"])
        assert slip.content.startswith(b"%PDF-")
        upload = client.post(f"/api/applications/{decision['application_id']}/salary-slip",
                             files={"file": ("payroll.pdf", slip.content, "application/pdf")})
        assert upload.status_code == 200, upload.text
        decision = upload.json()
    if status != "REJECT":
        assert decision["result"]["customer_name"] == profile["name"]
        assert client.get(decision["result"]["document"]["download_url"]).content.startswith(b"%PDF-")
    assert client.get("/api/mock/crm/SIMUL0000X").status_code == 404
