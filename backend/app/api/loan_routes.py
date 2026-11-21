from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.api_response import APIResponse, APIError
from app.dependencies import get_master_agent

router = APIRouter()


class LoanRequest(BaseModel):
    pan: str
    loan_amount: float = Field(gt=0, allow_inf_nan=False)
    tenure_months: int = Field(gt=0)
    monthly_income: float = Field(gt=0, allow_inf_nan=False)
    is_preapproved: bool = Field(False, deprecated=True, description="Legacy field. Offers are looked up server-side.")


@router.post("/apply-loan", response_model=APIResponse)
async def apply_loan(request: LoanRequest):
    master_agent = get_master_agent()

    result = await master_agent.process_loan_application(
        pan=request.pan,
        loan_amount=request.loan_amount,
        tenure_months=request.tenure_months,
        monthly_income=request.monthly_income,
    )

    stage = result.get("stage")
    payload = result.get("result")

    if payload.get("status") == "HOLD":
        return APIResponse(status="PENDING", stage=stage, data=payload, error=None)

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