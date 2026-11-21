from app.agents.loan_graph import compile_workflow
from app.services.applications import open_application, save_decision
from typing import Dict, Any
from app.services.customer_directory import active_profile, find_customer, use_profile
from app.core.logger import StructuredLogger

logger = StructuredLogger("MasterAgent")


class MasterAgent:
    def __init__(self, sales_agent, kyc_agent, credit_agent, sanction_agent):
        self.sales_agent = sales_agent
        self.kyc_agent = kyc_agent
        self.credit_agent = credit_agent
        self.sanction_agent = sanction_agent
        self.workflow = compile_workflow(self)

    # ----------------------------------------------------------
    # Stage-by-stage methods — called by ChatAgent at each step
    # ----------------------------------------------------------

    def consult_sales(self, loan_amount: float, tenure_months: int, monthly_income: float) -> Dict[str, Any]:
        logger.info("Sales agent consulted")
        return self.sales_agent.process_request(
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            monthly_income=monthly_income,
        )

    def consult_kyc(self, pan: str) -> Dict[str, Any]:
        logger.info("KYC agent consulted")
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
        request_key: str | None = None,
        phone: str = "", address: str = "",
    ) -> Dict[str, Any]:

        inputs = dict(phone=phone, address=address, pan=pan.strip().upper(), loan_amount=loan_amount,
                      tenure_months=tenure_months, monthly_income=monthly_income)
        if profile := active_profile.get():
            inputs["profile"] = profile.model_dump()
        row = open_application(inputs, request_key)
        if row["decision"]:
            return row["decision"]
        return await self.run_application(row)

    async def run_application(self, row, **evidence):
        digest = evidence.pop("slip_digest", None)
        with use_profile(row["inputs"].get("profile")):
            state = await self.workflow.ainvoke(dict(row["inputs"], application_id=row["id"], **evidence))
        decision = {"stage": state["stage"], "result": state["result"], "application_id": row["id"]}
        if state["result"].get("status") == "HOLD":
            if row["inputs"].get("profile"):
                decision["sample_slip_url"] = f"/api/applications/{row['id']}/sample-slip"
            else:
                customer = find_customer(row["inputs"]["pan"])
                decision["sample_slip_url"] = f"/api/mock/slips/{customer.customer_id}.pdf"
        if digest:
            decision["slip_digest"] = digest
        pdf = self.sanction_agent.render_pdf(state["result"]) if state["stage"] == "SANCTION" else None
        return save_decision(row, decision, pdf)
