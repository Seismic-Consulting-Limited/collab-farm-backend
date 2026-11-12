import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.farmer_schema import FarmerRead, PaginatedFarmerResponse
from app.services.farmer_service import FarmerService
from app.users import current_admin_user

router = APIRouter(prefix="/admin/farmers", tags=["Admin Farmer Verification"])


class FarmerVerificationReview(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=2000)


@router.get("/pending", response_model=PaginatedFarmerResponse)
async def list_pending_farmer_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).list_farmers_for_admin_review(page, page_size)


@router.patch(
    "/{farmer_id}/verification",
    response_model=FarmerRead,
    status_code=status.HTTP_200_OK,
)
async def review_farmer(
    farmer_id: uuid.UUID,
    payload: FarmerVerificationReview,
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).review_farmer(
        farmer_id=farmer_id,
        approved=payload.approved,
        note=payload.note,
    )
