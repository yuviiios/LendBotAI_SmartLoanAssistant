from time import perf_counter
from app.core.logger import StructuredLogger
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.dependencies import get_master_agent
from app.services.applications import load_application, read_letter
from app.services.customer_directory import find_customer
from app.services.demo_slips import SALARIES, payroll_pdf, sample_slip

router = APIRouter()
logger = StructuredLogger("SalaryEvidence")
MAX_SLIP_BYTES = 2 * 1024 * 1024


@router.get("/mock/slips/{customer_id}.pdf")
def demo_slip(customer_id: str):
    try:
        data = sample_slip(customer_id)
    except KeyError:
        raise HTTPException(404, "Unknown demo customer")
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="payslip-{customer_id}.pdf"'})


def salary_evidence(row):
    if profile := row["inputs"].get("profile"):
        salary = profile["monthly_salary"]
        return payroll_pdf(profile["name"], row["id"], salary), salary
    customer = find_customer(row["inputs"]["pan"])
    if not customer or customer.customer_id not in SALARIES:
        raise HTTPException(422, "No payroll record for this applicant.")
    return sample_slip(customer.customer_id), SALARIES[customer.customer_id]


@router.get("/applications/{application_id}/sample-slip")
def custom_slip(application_id: UUID):
    row = load_application(str(application_id))
    if not row or not row["inputs"].get("profile") or not (row["decision"] or {}).get("sample_slip_url"):
        raise HTTPException(404, "Sample slip unavailable")
    data, _ = salary_evidence(row)
    return Response(data, media_type="application/pdf", headers={
        "Cache-Control": "private, no-store", "Content-Disposition": 'attachment; filename="simulation-payslip.pdf"'})


@router.post("/applications/{application_id}/salary-slip")
async def submit_slip(application_id: UUID, file: UploadFile = File()):
    started = perf_counter()
    row = load_application(str(application_id))
    if not row or not row["decision"]:
        raise HTTPException(404, "Application unavailable")
    decision = row["decision"]
    data = await file.read(MAX_SLIP_BYTES + 1)
    if len(data) > MAX_SLIP_BYTES:
        raise HTTPException(413, "Choose a PDF smaller than 2 MB.")
    expected, salary = salary_evidence(row)
    if data != expected:
        raise HTTPException(422, "Choose the original demo salary slip for this applicant.")
    digest = sha256(data).hexdigest()
    if decision.get("slip_digest") == digest:
        return decision
    if decision["result"]["status"] != "HOLD":
        raise HTTPException(409, "This application is not waiting for a salary slip.")
    result = await get_master_agent().run_application(row, verified_salary=salary,
        previous_credit=decision["result"], slip_digest=digest)
    logger.info("salary_evidence_evaluated", result=result["result"]["status"],
                elapsed_ms=round((perf_counter() - started) * 1000))
    return result


@router.get("/applications/{application_id}/letter")
def download_letter(application_id: UUID):
    data = read_letter(str(application_id))
    if data is None:
        raise HTTPException(404, "Sanction letter unavailable")
    return Response(data, media_type="application/pdf", headers={"Cache-Control": "private, no-store",
        "Content-Disposition": f'attachment; filename="sanction-{application_id}.pdf"'})
