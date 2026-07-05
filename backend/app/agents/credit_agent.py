from typing import Optional, Dict, Any
from app.core.logger import StructuredLogger

logger = StructuredLogger("CreditAgent")


class CreditAgent:
    def __init__(self, credit_score_service):
        self.credit_score_service = credit_score_service

    async def fetch_credit_score(self, pan: str) -> Optional[int]:
        score = await self.credit_score_service.get_score(pan)
        return score

    def calculate_emi(self, loan_amount: float, roi: float, tenure_months: int) -> float:
        r = roi / (12 * 100)
        n = tenure_months
        if r == 0:
            return loan_amount / n
        emi = loan_amount * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
        return round(emi, 2)

    def evaluate_eligibility(
        self,
        score: int,
        loan_amount: float,
        monthly_income: float,
        tenure: int,
        is_preapproved: bool,
        documents: Dict[str, bool],
    ) -> Dict[str, Any]:

        # FIX: base context dict — loan_amount and tenure are now
        # included in EVERY return so SanctionAgent can read them
        base = {
            "score": score,
            "loan_amount": loan_amount,   # was missing — caused N/A in sanction letter
            "tenure": tenure,              # was missing — caused N/A in sanction letter
        }

        # --- 1. Score check ---
        if score >= 750:
            decision = "AUTO_APPROVE"
        elif 700 <= score <= 749:
            decision = "CONDITIONAL_APPROVE"
        else:
            return {
                **base,
                "status": "REJECT",
                "reason": f"Low credit score ({score}). Needs remediation.",
            }

        # --- 2. EMI check ---
        roi = 14
        emi = self.calculate_emi(loan_amount, roi, tenure)

        if emi > 0.5 * monthly_income:
            return {
                **base,
                "status": "REJECT",
                "reason": f"EMI ({emi}) exceeds 50% of monthly income ({monthly_income}).",
                "emi": emi,
            }

        # --- 3. Income cap check ---
        # FIX: this was at the bottom AFTER document checks — wrong order.
        # A user who fails income cap was getting HOLD instead of REJECT.
        if loan_amount > monthly_income * 2:
            return {
                **base,
                "status": "REJECT",
                "reason": "Requested loan exceeds 2× monthly income limit.",
                "emi": emi,
            }

        # --- 4. Pre-approved fast path ---
        if is_preapproved and loan_amount <= monthly_income * 2:
            return {
                **base,
                "status": "AUTO_APPROVE",
                "reason": "Pre-approved loan within limit.",
                "emi": emi,
            }

        # --- 5. Document checks (only after all numeric checks pass) ---
        if not documents.get("kyc_verified"):
            return {
                **base,
                "status": "ESCALATE",
                "reason": "KYC mismatch — manual verification required.",
                "missing_documents": ["kyc_verified"],
                "emi": emi,
            }

        missing_docs = []
        if not documents.get("payslip"):
            missing_docs.append("payslip")

        if missing_docs and decision == "CONDITIONAL_APPROVE":
            return {
                **base,
                "status": "HOLD",
                "reason": "Missing required documents.",
                "missing_documents": missing_docs,
                "emi": emi,
            }

        # --- Final approval ---
        return {
            **base,
            "status": decision,
            "emi": emi,
            "message": "Eligible for loan",
        }