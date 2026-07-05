from app.agents.kyc_agent import KycAgent


# -----------------------------
# Mock CRM Service
# -----------------------------
class MockCRMService:
    def fetch_kyc(self, pan: str):
        mock_data = {
            "VALID1234P": {
                "kyc_verified": True,
                "documents": {
                    "aadhaar": True,
                    "payslip": True,
                }
            },
            "NOKYC9999X": {
                "kyc_verified": False,
                "documents": {}
            },
            "MISSINGDOC1": {
                "kyc_verified": True,
                "documents": {
                    "aadhaar": True,
                    "payslip": False,
                }
            }
        }
        return mock_data.get(pan, {"kyc_verified": False, "documents": {}})


# -----------------------------
# Tests
# -----------------------------
def test_kyc_verified_and_complete():
    agent = KycAgent(MockCRMService())

    result = agent.verify_kyc("VALID1234P")

    assert result["status"] == "VERIFIED"
    assert result["documents"]["aadhaar"] is True


def test_kyc_not_verified():
    agent = KycAgent(MockCRMService())

    result = agent.verify_kyc("NOKYC9999X")

    assert result["status"] == "FAILED"
    assert "reason" in result


def test_kyc_missing_documents():
    agent = KycAgent(MockCRMService())

    result = agent.verify_kyc("MISSINGDOC1")

    assert result["status"] == "INCOMPLETE"
    assert "payslip" in result["missing_documents"]
