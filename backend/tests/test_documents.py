from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_upload_resumes_once_and_returns_a_pdf():
    client = TestClient(app)
    req = {"phone": "0000000001", "address": "11 Demo Lane", "pan": "ABCDE1234F", "loan_amount": 300000, "monthly_income": 40000,
           "tenure_months": 24, "request_id": str(uuid4())}
    first = client.post("/api/apply-loan", json=req).json()["data"]
    url = f"/api/applications/{first['application_id']}"
    assert client.post("/api/apply-loan", json=req).json()["data"] == first
    assert client.get(url + "/letter").status_code == 404
    for customer, status in [("C002", 422), ("C001", 200), ("C001", 200)]:
        slip = client.get(f"/api/mock/slips/{customer}.pdf").content
        response = client.post(url + "/salary-slip", files={"file": ("slip.pdf", slip, "application/pdf")})
        assert response.status_code == status
        if status == 200:
            approval = response.json()["result"]
            assert approval["status"] == "SANCTIONED"
            assert approval["terms"]["loan_amount"] == 300000
            assert approval["customer_name"] == "Asha Rao"
            pdf = client.get(approval["document"]["download_url"])
            assert pdf.content.startswith(b"%PDF-") and pdf.headers["content-type"] == "application/pdf"
    assert client.post("/api/apply-loan", json=dict(req, loan_amount=100000)).status_code == 409


def test_unaffordable_verified_salary_issues_no_letter():
    client = TestClient(app)
    data = client.post("/api/apply-loan", json={"phone": "0000000002", "address": "24 Sample Road", "pan": "PQRSX9999Z", "loan_amount": 140000,
                       "monthly_income": 200000, "tenure_months": 12}).json()["data"]
    url = f"/api/applications/{data['application_id']}"
    slip = client.get("/api/mock/slips/C002.pdf").content
    decision = client.post(url + "/salary-slip", files={"file": ("test.pdf", slip)}).json()
    assert decision["result"]["reason_code"] == "EMI_TOO_HIGH"
    assert client.get(url + "/letter").status_code == 404
