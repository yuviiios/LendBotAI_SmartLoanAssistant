from app.services.customer_directory import find_customer


class CreditScoreService:
    async def get_score(self, pan: str) -> int | None:
        customer = find_customer(pan)
        return customer.credit_score if customer else None
