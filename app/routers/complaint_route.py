import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.complaint_model import ComplaintCategory, ComplaintStatus
from app.models.user_model import User
from app.schemas.complaint_schema import (
    ComplaintCreatedResponse,
    ComplaintMessageRead,
    ComplaintPackageOption,
    ComplaintReviewerAssignment,
    ComplaintRead,
    ComplaintStatusUpdate,
    ComplaintSummaryResponse,
)
from app.services.complaint_service import ComplaintService
from app.users import current_active_user


router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.get("/categories", response_model=list[dict[str, str]])
async def get_complaint_categories(
    user: User = Depends(current_active_user),
):
    return [
        {"value": category.value, "label": category.value.replace("_", " ").title()}
        for category in ComplaintCategory
    ]


@router.get("/packages", response_model=list[ComplaintPackageOption])
async def get_related_package_options(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await ComplaintService(session).get_connected_packages(user)


@router.post(
    "",
    response_model=ComplaintCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def raise_complaint(
    subject: str = Form(..., min_length=3, max_length=200),
    category: ComplaintCategory = Form(...),
    description: str = Form(..., min_length=10, max_length=10000),
    package_id: Optional[uuid.UUID] = Form(None),
    acknowledgment_accepted: bool = Form(...),
    evidence: Optional[list[UploadFile]] = File(None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    complaint = await ComplaintService(session).create_complaint(
        user=user,
        subject=subject,
        category=category,
        description=description,
        package_id=package_id,
        acknowledgment_accepted=acknowledgment_accepted,
        evidence_files=evidence,
    )
    return {**complaint, "message": "Your complaint has been submitted."}


@router.get("", response_model=ComplaintSummaryResponse)
async def list_complaints(
    search: Optional[str] = Query(None, max_length=200),
    category: Optional[ComplaintCategory] = None,
    status_filter: Optional[ComplaintStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await ComplaintService(session).get_complaint_summary(
        user=user,
        search=search,
        category=category,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get("/{complaint_id}", response_model=ComplaintRead)
async def get_complaint(
    complaint_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await ComplaintService(session).get_complaint_detail(user, complaint_id)


@router.post("/{complaint_id}/messages", response_model=ComplaintMessageRead)
async def post_complaint_message(
    complaint_id: uuid.UUID,
    message: str = Form(..., min_length=1, max_length=10000),
    evidence: Optional[list[UploadFile]] = File(None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await ComplaintService(session).post_message(
        user=user,
        complaint_id=complaint_id,
        message=message,
        evidence_files=evidence,
    )


@router.patch("/{complaint_id}/reviewer", status_code=status.HTTP_200_OK)
async def assign_complaint_reviewer(
    complaint_id: uuid.UUID,
    payload: ComplaintReviewerAssignment,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await ComplaintService(session).assign_reviewer(
        actor=user,
        complaint_id=complaint_id,
        reviewer_id=payload.reviewer_id,
    )


@router.patch("/{complaint_id}/status", status_code=status.HTTP_200_OK)
async def update_complaint_status(
    complaint_id: uuid.UUID,
    payload: ComplaintStatusUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await ComplaintService(session).update_status(
        actor=user,
        complaint_id=complaint_id,
        new_status=payload.status,
        outcome=payload.outcome,
        explanation=payload.explanation,
    )


@router.post("/{complaint_id}/appeal", status_code=status.HTTP_200_OK)
async def appeal_complaint(
    complaint_id: uuid.UUID,
    reason: str = Form(..., min_length=1, max_length=5000),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await ComplaintService(session).appeal(user, complaint_id, reason)
