from typing import Dict, Any
from app.core.logger import StructuredLogger

logger = StructuredLogger("MasterAgent")


class MasterAgent:
    def __init__(self, sales_agent, kyc_agent, credit_agent, sanction_agent):
        self.sales_agent = sales_agent
        self.kyc_agent = kyc_agent
        self.credit_agent = credit_agent
        self.sanction_agent = sanction_agent

    async def process_loan_application(
        self,
        pan: str,
        loan_amount: float,
        tenure_months: int,
        monthly_income: float,
        is_preapproved: bool = False,
    ) -> Dict[str, Any]:

        # --- 1. Sales ---
        loan_request = self.sales_agent.process_request(
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            monthly_income=monthly_income,
        )

        if loan_request.get("status") == "REJECT":
            return {"stage": "SALES", "result": loan_request}

        # --- 2. KYC ---
        kyc_result = self.kyc_agent.verify_kyc(pan)

        if kyc_result["status"] in ("FAILED", "INCOMPLETE"):
            return {"stage": "KYC", "result": kyc_result}

        documents = kyc_result.get("documents", {})

        # --- 3. Credit ---
        score = await self.credit_agent.fetch_credit_score(pan)

        credit_decision = self.credit_agent.evaluate_eligibility(
            score=score,
            loan_amount=loan_request["loan_amount"],
            monthly_income=loan_request["monthly_income"],
            tenure=loan_request["tenure_months"],
            is_preapproved=is_preapproved,
            documents={
                "payslip": documents.get("payslip", False),
                "kyc_verified": True,
            },
        )

        if credit_decision["status"] not in ("AUTO_APPROVE", "CONDITIONAL_APPROVE"):
            return {"stage": "CREDIT", "result": credit_decision}

        # --- 4. Sanction ---
        # FIX: credit_decision now already contains loan_amount and tenure
        # (set in credit_agent.py via the base dict) so SanctionAgent
        # can read them directly — no extra forwarding needed here.
        sanction_result = self.sanction_agent.sanction_loan(credit_decision)

        return {"stage": "SANCTION", "result": sanction_result}