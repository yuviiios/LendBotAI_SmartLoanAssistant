from typing import Any, Optional
from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    message: str


class APIResponse(BaseModel):
    status: str  # SUCCESS or FAILURE
    stage: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[APIError] = None
