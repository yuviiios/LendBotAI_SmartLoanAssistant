from typing import Dict, Any
from app.services.customer_directory import find_customer
from app.core.logger import StructuredLogger

logger = StructuredLogger("MasterAgent")


class MasterAgent:
    def __init__(self, sales_agent, kyc_agent, credit_agent, sanction_agent):
        self.sales_agent = sales_agent
        self.kyc_agent = kyc_agent
        self.credit_agent = credit_agent
        self.sanction_agent = sanction_agent

    # ----------------------------------------------------------
    # Stage-by-stage methods — called by ChatAgent at each step
    # ----------------------------------------------------------

    def consult_sales(self, loan_amount: float, tenure_months: int, monthly_income: float) -> Dict[str, Any]:
        logger.info("Sales agent consulted", loan_amount=loan_amount, tenure=tenure_months)
        return self.sales_agent.process_request(
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            monthly_income=monthly_income,
        )

    def consult_kyc(self, pan: str) -> Dict[str, Any]:
        logger.info("KYC agent consulted", pan=pan)
        return self.kyc_agent.verify_kyc(pan)

    async def consult_credit(self, pan: str, loan_amount: float, tenure: int) -> dict:
        customer = find_customer(pan)
        score = await self.credit_agent.fetch_credit_score(pan)
        if customer is None or score is None:
            return {"status": "ESCALATE", "reason_code": "MISSING_RECORD",
                    "reason": "The offer or credit record could not be retrieved."}
        return self.credit_agent.evaluate_eligibility(
            score=score, loan_amount=loan_amount, tenure=tenure,
            preapproved_limit=customer.preapproved_limit,
        )

    def consult_sanction(self, credit_decision: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Sanction agent consulted")
        return self.sanction_agent.sanction_loan(credit_decision)

    def get_product_info(self) -> Dict[str, Any]:
        return self.sales_agent.explain_products()

    def validate_pan(self, pan: str) -> Dict[str, Any]:
        return self.kyc_agent.validate_pan_format(pan)

    def validate_loan_params(self, loan_amount: float, tenure_months: int) -> Dict[str, Any]:
        return self.sales_agent.validate_loan_parameters(loan_amount, tenure_months)

    # ----------------------------------------------------------
    # Shared processing pipeline for confirmed chat and direct applications
    # ----------------------------------------------------------

    async def process_loan_application(
        self,
        pan: str,
        loan_amount: float,
        tenure_months: int,
        monthly_income: float,
        is_preapproved: bool = False,
    ) -> Dict[str, Any]:

        # --- 1. Sales ---
        loan_request = self.consult_sales(loan_amount, tenure_months, monthly_income)

        if loan_request.get("status") == "REJECT":
            return {"stage": "SALES", "result": loan_request}

        # --- 2. KYC ---
        kyc_result = self.consult_kyc(pan)

        if kyc_result["status"] in ("FAILED", "INCOMPLETE"):
            return {"stage": "KYC", "result": kyc_result}

        credit_decision = await self.consult_credit(
            pan, loan_request["loan_amount"], loan_request["tenure_months"]
        )

        if credit_decision["status"] not in ("AUTO_APPROVE", "CONDITIONAL_APPROVE"):
            return {"stage": "CREDIT", "result": credit_decision}

        # --- 4. Sanction ---
        sanction_result = self.consult_sanction(credit_decision)

        return {"stage": "SANCTION", "result": sanction_result}