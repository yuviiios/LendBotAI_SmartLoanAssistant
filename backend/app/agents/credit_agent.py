from decimal import Decimal, ROUND_HALF_UP


class CreditAgent:
    POLICY_VERSION = "offer-v1"

    def __init__(self, credit_score_service):
        self.credit_score_service = credit_score_service

    async def fetch_credit_score(self, pan: str) -> int | None:
        return await self.credit_score_service.get_score(pan)

    def calculate_emi(self, loan_amount: float, roi: float, tenure_months: int) -> float:
        principal = Decimal(str(loan_amount))
        rate = Decimal(str(roi)) / 1200
        instalment = principal / tenure_months if not rate else (
            principal * rate / (1 - (1 + rate) ** -tenure_months)
        )
        return float(instalment.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def evaluate_eligibility(
        self, *, score: int, loan_amount: float, tenure: int, preapproved_limit: int,
        annual_rate: float = 14, verified_monthly_salary: float | None = None,
    ) -> dict:
        """Evaluate a verified customer's offer. Salary must come from accepted evidence."""
        emi = self.calculate_emi(loan_amount, annual_rate, tenure)
        result = {
            "policy_version": self.POLICY_VERSION, "score": score, "emi": emi,
            "loan_amount": loan_amount, "tenure": tenure, "annual_rate": annual_rate,
            "preapproved_limit": preapproved_limit,
        }
        if score < 700:
            return dict(result, status="REJECT", reason_code="LOW_SCORE", reason="Credit score below 700.")
        if loan_amount > 2 * preapproved_limit:
            return dict(result, status="REJECT", reason_code="ABOVE_MAXIMUM",
                        reason="The requested amount exceeds twice your pre-approved limit.")
        if loan_amount <= preapproved_limit:
            return dict(result, status="AUTO_APPROVE", reason_code="WITHIN_OFFER",
                        reason="The requested amount is within your pre-approved offer.")
        if verified_monthly_salary is None:
            return dict(result, status="HOLD", reason_code="SALARY_SLIP_REQUIRED",
                        reason="A salary slip is required because the amount exceeds your pre-approved limit.",
                        missing_documents=["payslip"])
        if Decimal(str(emi)) * 2 > Decimal(str(verified_monthly_salary)):
            return dict(result, status="REJECT", reason_code="EMI_TOO_HIGH",
                        reason="The EMI exceeds half of your verified monthly salary.")
        return dict(result, status="CONDITIONAL_APPROVE", reason_code="SALARY_VERIFIED",
                    reason="The verified salary meets the EMI requirement.")
