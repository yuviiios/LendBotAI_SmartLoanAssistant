from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.dependencies import get_master_agent
from app.services.applications import load_application, read_letter
from app.services.customer_directory import find_customer
from app.services.demo_slips import SALARIES, sample_slip

router = APIRouter()
MAX_SLIP_BYTES = 2 * 1024 * 1024


@router.get("/mock/slips/{customer_id}.pdf")
def demo_slip(customer_id: str):
    try:
        data = sample_slip(customer_id)
    except KeyError:
        raise HTTPException(404, "Unknown demo customer")
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="payslip-{customer_id}.pdf"'})


@router.post("/applications/{application_id}/salary-slip")
async def submit_slip(application_id: UUID, file: UploadFile = File()):
    row = load_application(str(application_id))
    if not row or not row["decision"]:
        raise HTTPException(404, "Application unavailable")
    decision = row["decision"]
    data = await file.read(MAX_SLIP_BYTES + 1)
    if len(data) > MAX_SLIP_BYTES:
        raise HTTPException(413, "Choose a PDF smaller than 2 MB.")
    customer = find_customer(row["inputs"]["pan"])
    if not customer or not data.startswith(b"%PDF-") or data != sample_slip(customer.customer_id):
        raise HTTPException(422, "Choose the original demo salary slip for this applicant.")
    digest = sha256(data).hexdigest()
    if decision.get("slip_digest") == digest:
        return decision
    if decision["result"]["status"] != "HOLD":
        raise HTTPException(409, "This application is not waiting for a salary slip.")
    return await get_master_agent().run_application(row, verified_salary=SALARIES[customer.customer_id],
        previous_credit=decision["result"], slip_digest=digest)


@router.get("/applications/{application_id}/letter")
def download_letter(application_id: UUID):
    data = read_letter(str(application_id))
    if data is None:
        raise HTTPException(404, "Sanction letter unavailable")
    return Response(data, media_type="application/pdf", headers={"Cache-Control": "private, no-store",
        "Content-Disposition": f'attachment; filename="sanction-{application_id}.pdf"'})
