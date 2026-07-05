from typing import Dict, Any
from app.core.logger import StructuredLogger

logger = StructuredLogger("SalesAgent")


class SalesAgent:
    def __init__(self, supported_products: Dict[str, Dict[str, Any]] | None = None):
        self.supported_products = supported_products or {
            "personal_loan": {
                "min_amount": 50000,
                "max_amount": 2000000,
                "min_tenure": 6,
                "max_tenure": 60,
            }
        }

    def validate_input(self, loan_amount: float, tenure_months: int, monthly_income: float):
        if loan_amount <= 0:
            raise ValueError("Loan amount must be positive")
        if tenure_months <= 0:
            raise ValueError("Tenure must be positive")
        if monthly_income <= 0:
            raise ValueError("Monthly income must be positive")

    def match_product(self, loan_amount: float, tenure_months: int) -> str | None:
        for product_name, rules in self.supported_products.items():
            if (
                rules["min_amount"] <= loan_amount <= rules["max_amount"]
                and rules["min_tenure"] <= tenure_months <= rules["max_tenure"]
            ):
                return product_name
        return None

    def build_loan_request(
        self,
        loan_amount: float,
        tenure_months: int,
        monthly_income: float,
    ) -> Dict[str, Any]:
        self.validate_input(loan_amount, tenure_months, monthly_income)

        product = self.match_product(loan_amount, tenure_months)

        if product is None:
            logger.info(
                message="No suitable loan product found",
                loan_amount=loan_amount,
                tenure_months=tenure_months
            )

            return {
                "status": "REJECT",
                "reason": "No suitable loan product available"
            }

        return {
            "loan_amount": loan_amount,
            "tenure_months": tenure_months,
            "monthly_income": monthly_income,
            "loan_type": product,
        }

    def process_request(self, loan_amount: float, tenure_months: int, monthly_income: float):
        return self.build_loan_request(loan_amount, tenure_months, monthly_income)
