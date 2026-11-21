"""Read-only endpoints backed exclusively by the synthetic demo directory."""
from fastapi import APIRouter, Depends, HTTPException

from app.services.customer_directory import Customer, find_customer

router = APIRouter(prefix="/mock", tags=["Synthetic customer systems"])


def known_customer(pan: str) -> Customer:
    customer = find_customer(pan)
    if customer is None:
        raise HTTPException(404, "Unknown demo customer")
    return customer


@router.get("/crm/{pan}")
def crm(customer: Customer = Depends(known_customer)):
    return customer.model_dump(exclude={"credit_score", "preapproved_limit"})


@router.get("/offers/{pan}")
def offer(customer: Customer = Depends(known_customer)):
    return customer.model_dump(include={"customer_id", "preapproved_limit"})


@router.get("/bureau/{pan}")
def bureau(customer: Customer = Depends(known_customer)):
    return {"customer_id": customer.customer_id, "credit_score": customer.credit_score, "scale_max": 900}
