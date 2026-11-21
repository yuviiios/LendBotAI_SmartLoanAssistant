from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas


class SanctionAgent:
    def sanction_loan(self, credit_decision):
        status = credit_decision.get("status")
        if status not in ("AUTO_APPROVE", "CONDITIONAL_APPROVE"):
            return {"status": "NOT_SANCTIONED", "credit_status": status,
                    "reason": "Loan not eligible for sanction"}
        reference = credit_decision.get("application_id") or str(uuid4())
        return {
            "status": "SANCTIONED", "sanction_id": reference,
            "sanction_date": datetime.now(timezone.utc).isoformat(),
            "customer_name": credit_decision.get("customer_name", "Demo applicant"),
            "approved_score": credit_decision["score"], "approved_emi": credit_decision["emi"],
            "policy_version": credit_decision.get("policy_version"),
            "terms": {"loan_amount": credit_decision["loan_amount"], "tenure_months": credit_decision["tenure"],
                      "interest_rate": credit_decision.get("annual_rate", 14)},
            "document": {"type": "SANCTION_LETTER", "file_name": f"sanction_{reference}.pdf",
                         "download_url": f"/api/applications/{reference}/letter"},
        }

    @staticmethod
    def render_pdf(approval):
        out = BytesIO()
        pdf = Canvas(out, pagesize=A4, invariant=True)
        pdf.setTitle("Personal loan sanction letter")
        pdf.setFillColor(HexColor("#134C43"))
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawString(48, 765, "Personal loan sanction letter")
        pdf.setFillColor(HexColor("#263633"))
        pdf.setFont("Helvetica", 11)
        pdf.drawString(48, 728, f"Reference  {approval['sanction_id']}")
        pdf.drawString(48, 706, f"Issued  {approval['sanction_date'][:10]}")
        pdf.drawString(48, 659, f"Dear {approval['customer_name']},")
        pdf.drawString(48, 635, "Your personal loan has been approved on the following terms.")
        terms = approval["terms"]
        for y, label, value in [
            (575, "Approved principal", f"INR {terms['loan_amount']:,.2f}"),
            (535, "Annual interest rate", f"{terms['interest_rate']}%"),
            (495, "Repayment period", f"{terms['tenure_months']} months"),
            (455, "Monthly instalment", f"INR {approval['approved_emi']:,.2f}"),
        ]:
            pdf.drawString(48, y, label)
            pdf.drawRightString(540, y, value)
            pdf.line(48, y-12, 540, y-12)
        pdf.drawString(48, 85, "LendBot AI | Synthetic demonstration letter")
        pdf.save()
        return out.getvalue()
