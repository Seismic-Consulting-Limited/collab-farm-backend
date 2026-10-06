import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class InvestmentCreateRequest(BaseModel):
    package_id: uuid.UUID
    amount: float = Field(..., gt=0, description="Amount to invest in Naira")


class InvestmentResponse(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    farming_category: str
    amount: float
    roi_percentage: float
    expected_returns: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)