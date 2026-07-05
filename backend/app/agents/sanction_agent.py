from typing import Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
import os

from app.core.logger import StructuredLogger

logger = StructuredLogger("SanctionAgent")


class SanctionAgent:
    # FIX: was "app/static/outputs" — relative path breaks on Render because
    # the server working directory is not guaranteed to be the project root.
    # Built as absolute path from this file's location — always resolves correctly.
    OUTPUT_DIR = os.path.join(
        os.path.dirname(                    # app/agents/file_name->agents
            os.path.dirname(                # app/agents->app
                os.path.abspath(__file__)
            )
        ),
        "static", "outputs"
    )

    def sanction_loan(self, credit_decision: Dict[str, Any]) -> Dict[str, Any]:
        status = credit_decision.get("status")

        if status not in ("AUTO_APPROVE", "CONDITIONAL_APPROVE"):
            logger.info("Loan not eligible for sanction", credit_status=status)
            return {
                "status": "NOT_SANCTIONED",
                "reason": "Loan not eligible for sanction",
                "credit_status": status,
            }

        sanction_id = str(uuid4())
        sanction_date = datetime.now(timezone.utc).isoformat()
        file_name = f"sanction_{sanction_id}.txt"
        file_path = os.path.join(self.OUTPUT_DIR, file_name)

        self._generate_sanction_letter(
            file_path=file_path,
            credit_decision=credit_decision,
            sanction_id=sanction_id,
            sanction_date=sanction_date,
        )

        logger.info("Loan sanctioned", sanction_id=sanction_id, credit_status=status)

        return {
            "status": "SANCTIONED",
            "sanction_id": sanction_id,
            "sanction_date": sanction_date,
            "approved_emi": credit_decision.get("emi"),
            "approved_score": credit_decision.get("score"),
            "terms": {
                "interest_rate": 14,
                "tenure_months": credit_decision.get("tenure"),
            },
            "document": {
                "type": "SANCTION_LETTER",
                "file_name": file_name,
                "download_url": f"/static/outputs/{file_name}",
            },
        }

    def _generate_sanction_letter(
        self,
        file_path: str,
        credit_decision: Dict[str, Any],
        sanction_id: str,
        sanction_date: str,
    ) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        loan_amount = credit_decision.get("loan_amount", "N/A")
        tenure = credit_decision.get("tenure", "N/A")
        emi = credit_decision.get("emi", "N/A")
        score = credit_decision.get("score", "N/A")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"""
SANCTION LETTER
===========================

Sanction ID   : {sanction_id}
Sanction Date : {sanction_date}

Approved Loan Details
---------------------
Loan Amount   : Rs. {loan_amount:,.2f}
Tenure        : {tenure} months
Interest Rate : 14%
EMI           : Rs. {emi:,.2f}
Credit Score  : {score}

This loan has been sanctioned based on automated credit assessment.

-- AI Loan Processing System
""")