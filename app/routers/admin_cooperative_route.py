import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.profile_schema import (
    AdminCooperativeReviewItem,
    PaginatedAdminCooperativeReviewResponse,
)
from app.services.profile_service import ProfileService
from app.users import current_admin_user

router = APIRouter(
    prefix="/admin/cooperatives", tags=["Admin Cooperative Verification"]
)


class CooperativeVerificationReview(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=2000)


@router.get("/pending", response_model=PaginatedAdminCooperativeReviewResponse)
async def list_pending_cooperative_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProfileService(db).list_pending_cooperative_reviews(page, page_size)


@router.patch(
    "/{cooperative_id}/verification",
    response_model=AdminCooperativeReviewItem,
    status_code=status.HTTP_200_OK,
)
async def review_cooperative(
    cooperative_id: uuid.UUID,
    payload: CooperativeVerificationReview,
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProfileService(db).review_cooperative(
        cooperative_id=cooperative_id,
        approved=payload.approved,
        note=payload.note,
    )
