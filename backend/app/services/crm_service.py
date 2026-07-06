import re
import hashlib


class CRMService:
    # Test PANs with specific document scenarios
    FIXED_KYC = {
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

    def fetch_kyc(self, pan: str):
        if pan in self.FIXED_KYC:
            return self.FIXED_KYC[pan]

        # Any valid PAN format → generate KYC dynamically from hash
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
            return {"kyc_verified": False, "documents": {}}

        # Deterministic document availability from PAN hash
        # ~85% have payslip, ~95% have aadhaar (realistic distribution)
        hash_val = int(hashlib.sha256(pan.encode()).hexdigest(), 16)
        has_payslip = (hash_val % 100) < 85
        has_aadhaar = (hash_val % 100) < 95

        return {
            "kyc_verified": True,
            "documents": {"payslip": has_payslip, "aadhaar": has_aadhaar},
        }
