"""Synthetic demo records shared by the CRM, offer mart and credit bureau."""
import csv
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Customer(BaseModel):
    model_config = ConfigDict(frozen=True)
    customer_id: str
    pan: str
    name: str
    age: int
    city: str
    phone: str
    address: str
    segment: str
    current_loan_type: str
    outstanding_principal: int
    credit_score: int = Field(ge=0, le=900)
    preapproved_limit: int = Field(gt=0)


@lru_cache(maxsize=1)
def customers_by_pan() -> dict[str, Customer]:
    with Path(__file__).with_name("customers.csv").open(encoding="utf-8", newline="") as source:
        records = (Customer.model_validate(row) for row in csv.DictReader(source))
        return {record.pan: record for record in records}


def find_customer(pan: str) -> Customer | None:
    return customers_by_pan().get(pan.strip().upper())
