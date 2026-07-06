import re
from typing import Dict, Any
from app.core.logger import StructuredLogger

logger = StructuredLogger("KycAgent")

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


class KycAgent:
    """
    KycAgent responsibilities:
    - Validate PAN format in real-time during collection
    - Verify customer identity (KYC) against CRM
    - Check document completeness
    - Decide whether application can proceed
    """

    def __init__(self, crm_service):
        self.crm_service = crm_service

    def validate_pan_format(self, pan: str) -> Dict[str, Any]:
        pan = pan.strip().upper()
        if not PAN_REGEX.match(pan):
            logger.info("PAN format invalid", pan=pan)
            return {
                "status": "INVALID",
                "reason": "PAN must be 10 characters: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)",
            }
        logger.info("PAN format valid", pan=pan)
        return {"status": "VALID", "pan": pan}

    def verify_kyc(self, pan: str) -> Dict[str, Any]:
        kyc_data = self.crm_service.fetch_kyc(pan)

        if not kyc_data.get("kyc_verified"):
            logger.info("KYC verification failed", pan=pan)
            return {"status": "FAILED", "reason": "KYC not verified"}

        documents = kyc_data.get("documents", {})
        missing_docs = [doc for doc, present in documents.items() if not present]

        if missing_docs:
            logger.info("KYC incomplete", pan=pan, missing=missing_docs)
            return {"status": "INCOMPLETE", "missing_documents": missing_docs}

        logger.info("KYC verified", pan=pan)
        return {"status": "VERIFIED", "documents": documents}