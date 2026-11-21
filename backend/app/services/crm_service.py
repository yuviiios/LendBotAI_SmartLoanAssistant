from app.services.customer_directory import find_customer


class CRMService:
    def fetch_kyc(self, pan: str) -> dict:
        customer = find_customer(pan)
        if customer is None:
            return {"kyc_verified": False, "documents": {}}
        return {
            "phone": customer.phone, "address": customer.address,
            "customer_id": customer.customer_id,
            "kyc_verified": True,
            "documents": {"aadhaar": True},
        }
