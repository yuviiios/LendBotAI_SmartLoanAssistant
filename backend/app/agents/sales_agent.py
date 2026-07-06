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
                "interest_rate": 14,
                "processing_fee": "1-2%",
                "prepayment": "Allowed after 6 EMIs",
            }
        }

    def explain_products(self) -> Dict[str, Any]:
        products = []
        for name, rules in self.supported_products.items():
            products.append({
                "name": name.replace("_", " ").title(),
                "amount_range": f"₹{rules['min_amount']:,.0f} – ₹{rules['max_amount']:,.0f}",
                "tenure_range": f"{rules['min_tenure']} – {rules['max_tenure']} months",
                "interest_rate": f"{rules.get('interest_rate', 14)}% p.a.",
                "processing_fee": rules.get("processing_fee", "1-2%"),
                "prepayment": rules.get("prepayment", "Allowed after 6 EMIs"),
            })
        logger.info("Product info requested", products_count=len(products))
        return {"status": "OK", "products": products}

    def validate_loan_parameters(self, loan_amount: float, tenure_months: int) -> Dict[str, Any]:
        product = self.match_product(loan_amount, tenure_months)
        if product is None:
            reasons = []
            for _, rules in self.supported_products.items():
                if loan_amount < rules["min_amount"]:
                    reasons.append(f"Minimum loan amount is ₹{rules['min_amount']:,.0f}")
                elif loan_amount > rules["max_amount"]:
                    reasons.append(f"Maximum loan amount is ₹{rules['max_amount']:,.0f}")
                if tenure_months < rules["min_tenure"]:
                    reasons.append(f"Minimum tenure is {rules['min_tenure']} months")
                elif tenure_months > rules["max_tenure"]:
                    reasons.append(f"Maximum tenure is {rules['max_tenure']} months")
            return {"status": "INVALID", "reasons": reasons}
        return {"status": "VALID", "product": product}

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
