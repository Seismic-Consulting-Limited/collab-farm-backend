import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User, UserRole
from app.schemas.disbursement_schema import (
    DisbursementDetailResponse,
    PaginatedDisbursementResponse,
)
from app.services.disbursement_service import DisbursementService
from app.users import current_active_user

router = APIRouter(prefix="/disbursements", tags=["Disbursements"])


@router.get("", response_model=PaginatedDisbursementResponse, status_code=status.HTTP_200_OK)
async def get_disbursements(
    search: Optional[str] = Query(None, description="Search by package name or farming cycle"),
    package_type: Optional[str] = Query(None, description="Filter by package category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by package status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    cooperative_id = user.id if getattr(user, "role", None) == UserRole.COOPERATIVE else None

    return await DisbursementService(db).get_disbursements_overview(
        cooperative_id=cooperative_id,
        search=search,
        package_type=package_type,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get("/{package_id}", response_model=DisbursementDetailResponse, status_code=status.HTTP_200_OK)
async def get_disbursement_detail(
    package_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await DisbursementService(db).get_disbursement_detail(package_id)