from typing import Dict, Any
from app.core.logger import StructuredLogger

# FIX: was StructuredLogger("SalesAgent") — KYC logs appeared as SalesAgent in output
logger = StructuredLogger("KycAgent")


class KycAgent:
    """
    KycAgent responsibilities:
    - Verify customer identity (KYC)
    - Check document completeness
    - Decide whether application can proceed
    """

    def __init__(self, crm_service):
        self.crm_service = crm_service

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