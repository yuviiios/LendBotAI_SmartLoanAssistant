from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.api_response import APIResponse, APIError
from app.dependencies import get_master_agent

router = APIRouter()


class LoanRequest(BaseModel):
    pan: str
    loan_amount: float
    tenure_months: int
    monthly_income: float
    is_preapproved: bool = False


@router.post("/apply-loan", response_model=APIResponse)
async def apply_loan(request: LoanRequest):
    master_agent = get_master_agent()

    result = await master_agent.process_loan_application(
        pan=request.pan,
        loan_amount=request.loan_amount,
        tenure_months=request.tenure_months,
        monthly_income=request.monthly_income,
        is_preapproved=request.is_preapproved,
    )

    stage = result.get("stage")
    payload = result.get("result")

    if stage == "SANCTION":
        return APIResponse(status="SUCCESS", stage=stage, data=payload, error=None)

    return APIResponse(
        status="FAILURE",
        stage=stage,
        data=None,
        error=APIError(
            code=payload.get("status", "UNKNOWN_ERROR"),
            message=payload.get("reason", "Request could not be processed"),
        ),
    )