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


@router.get("", response_model=PaginatedFarmerResponse)
async def list_farmers_for_admin(
    search: str | None = Query(None),
    farming_category: str | None = Query(None),
    cooperative_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List farmer profiles for admin viewing, including their farms."""
    return await FarmerService(db).list_farmers(
        search=search,
        farming_category=farming_category,
        cooperative_id=cooperative_id,
        page=page,
        page_size=page_size,
    )


@router.get("/{farmer_id}", response_model=FarmerRead)
async def get_farmer_for_admin(
    farmer_id: uuid.UUID,
    _admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return a farmer's full profile and farm list for read-only admin use."""
    return await FarmerService(db).get_farmer_profile(farmer_id)


@router.patch(
    "/{farmer_id}/verification",
    response_model=FarmerRead,
    status_code=status.HTTP_200_OK,
)
async def review_farmer(
    farmer_id: uuid.UUID,
    payload: FarmerVerificationReview,
    admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).review_farmer(
        farmer_id=farmer_id,
        approved=payload.approved,
        admin=admin,
        note=payload.note,
    )
