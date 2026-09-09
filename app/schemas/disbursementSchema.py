import uuid
from decimal import Decimal
from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class DisbursementStatus(str, Enum):
    PENDING = "PENDING"
    MILESTONE_SUBMITTED = "MILESTONE_SUBMITTED"
    DISBURSED = "DISBURSED"
    FAILED = "FAILED"
    
class MilestoneSubmitSchema(BaseModel):
    milestone_proof_url: str
    notes: Optional[str] = None

class DisbursementReleaseSchema(BaseModel):
    transaction_reference: str
    notes: Optional[str] = None
    
class DisbursementReadSchema(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    tranche_number: int
    amount: Decimal
    date: date
    milestone_description: str
    disbursement_status: DisbursementStatus
    milestone_proof_url: Optional[str] = None
    transaction_reference: Optional[str] =None
    disbursed_at: Optional[datetime] = None