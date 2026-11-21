"""Synthetic demo records shared by the CRM, offer mart and credit bureau."""
import csv
from contextlib import contextmanager
from contextvars import ContextVar
from typing import ClassVar
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


class SimulationProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    # A reserved fictional PAN only resolves inside this profile's request.
    pan: ClassVar[str] = "SIMUL0000X"
    name: str = Field(min_length=1, max_length=60)
    phone: str = Field(pattern=r"^[0-9]{10}$")
    address: str = Field(min_length=3, max_length=120)
    credit_score: int = Field(ge=0, le=900)
    preapproved_limit: int = Field(ge=1, le=2000000)
    monthly_salary: int = Field(ge=1, le=10000000)
    customer_id: ClassVar[str] = "CUSTOM"


active_profile: ContextVar[SimulationProfile | None] = ContextVar("active_profile", default=None)


@contextmanager
def use_profile(data):
    token = active_profile.set(SimulationProfile.model_validate(data) if data else None)
    try:
        yield
    finally:
        active_profile.reset(token)


def find_customer(pan: str) -> Customer | SimulationProfile | None:
    if profile := active_profile.get():
        return profile if pan.strip().upper() == profile.pan else None
    return customers_by_pan().get(pan.strip().upper())
