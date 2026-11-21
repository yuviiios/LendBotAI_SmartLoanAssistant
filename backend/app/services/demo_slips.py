"""Reproducible synthetic payslips for the demo. Verification requires an exact fixture."""
from functools import lru_cache
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from app.services.customer_directory import customers_by_pan

SALARIES = dict(zip((f"C{i:03}" for i in range(1, 11)),
                    (60000, 12000, 35000, 48000, 51000, 80000, 44000, 70000, 27000, 89000)))


@lru_cache(maxsize=10)
def sample_slip(customer_id):
    customer = next((c for c in customers_by_pan().values() if c.customer_id == customer_id), None)
    if customer is None:
        raise KeyError(customer_id)
    out = BytesIO()
    pdf = Canvas(out, invariant=True)
    pdf.setTitle("Synthetic monthly salary slip")
    pdf.drawString(55, 760, "Demonstration payroll | Monthly salary slip")
    pdf.drawString(55, 710, f"Employee: {customer.name} ({customer.customer_id})")
    pdf.drawString(55, 682, f"Net monthly salary: INR {SALARIES[customer_id]:,.2f}")
    pdf.drawString(55, 620, "Synthetic document for the LendBot demo")
    pdf.save()
    return out.getvalue()
