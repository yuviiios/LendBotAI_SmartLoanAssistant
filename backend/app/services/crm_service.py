class CRMService:
    def fetch_kyc(self, pan: str):
        # FIX: LOWSC0000X was missing here but existed in CreditScoreService.
        # All 3 test PANs now exist in both services so test scenarios are consistent:
        #   ABCDE1234F → good customer (score 780, all docs)
        #   PQRSX9999Z → missing payslip (score 720, conditional path)
        #   LOWSC0000X → low credit score customer (score 650, reject path)
        mock_db = {
            "ABCDE1234F": {
                "kyc_verified": True,
                "documents": {"payslip": True, "aadhaar": True},
            },
            "PQRSX9999Z": {
                "kyc_verified": True,
                "documents": {"payslip": False, "aadhaar": True},
            },
            "LOWSC0000X": {
                "kyc_verified": True,
                "documents": {"payslip": True, "aadhaar": True},
            },
        }
        return mock_db.get(pan, {"kyc_verified": False, "documents": {}})