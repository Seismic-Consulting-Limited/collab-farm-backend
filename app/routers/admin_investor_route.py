import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.profile_schema import (
    AdminInvestorReviewItem,
    PaginatedAdminInvestorReviewResponse,
)
from app.services.profile_service import ProfileService
from app.users import current_admin_user

router = APIRouter(prefix="/admin/investors", tags=["Admin Investor Verification"])


class InvestorVerificationReview(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=2000)


@router.get("/pending", response_model=PaginatedAdminInvestorReviewResponse)
async def list_pending_investor_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProfileService(db).list_pending_investor_reviews(page, page_size)


@router.patch(
    "/{investor_id}/verification",
    response_model=AdminInvestorReviewItem,
    status_code=status.HTTP_200_OK,
)
async def review_investor(
    investor_id: uuid.UUID,
    payload: InvestorVerificationReview,
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProfileService(db).review_investor(
        investor_id=investor_id,
        approved=payload.approved,
        note=payload.note,
    )
