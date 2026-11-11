import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.complaint_model import ComplaintCategory, ComplaintStatus
from pydantic import Field


class ComplaintMessageRead(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    author_role: str
    message: str
    evidence: list[dict[str, Any]]
    created_at: datetime


class ComplaintActionRead(BaseModel):
    id: uuid.UUID
    action: str
    description: str
    actor_id: Optional[uuid.UUID] = None
    actor_name: str
    created_at: datetime


class ComplaintRead(BaseModel):
    id: uuid.UUID
    reference: str
    submitted_by_id: uuid.UUID
    package_id: Optional[uuid.UUID]
    package_title: Optional[str] = None
    raised_by_name: Optional[str] = None
    raised_by_role: Optional[str] = None
    cooperative_id: Optional[uuid.UUID] = None
    cooperative_name: Optional[str] = None
    assigned_reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    subject: str
    category: ComplaintCategory
    description: str
    evidence: list[dict[str, Any]]
    status: ComplaintStatus
    acknowledgment_accepted: bool
    outcome: Optional[str] = None
    explanation: Optional[str] = None
    messages: list[ComplaintMessageRead] = Field(default_factory=list)
    actions: list[ComplaintActionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintPackageOption(BaseModel):
    id: uuid.UUID
    title: str


class ComplaintCreatedResponse(ComplaintRead):
    message: str = "Your complaint has been submitted."


class ComplaintSummaryItem(BaseModel):
    id: uuid.UUID
    reference: str
    subject: str
    category: ComplaintCategory
    package_id: Optional[uuid.UUID] = None
    package_title: Optional[str] = None
    raised_by_id: uuid.UUID
    raised_by_name: str
    raised_by_role: str
    status: ComplaintStatus
    created_at: datetime


class ComplaintSummaryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    open_count: int
    under_review_count: int
    awaiting_response_count: int
    resolved_count: int
    escalated_count: int
    items: list[ComplaintSummaryItem]


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus
    outcome: Optional[str] = None
    explanation: Optional[str] = None


class ComplaintReviewerAssignment(BaseModel):
    reviewer_id: uuid.UUID
