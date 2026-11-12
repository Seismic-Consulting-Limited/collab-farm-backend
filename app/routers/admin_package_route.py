import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.package_schema import (
    PackageAdminReview,
    PackageDetailRead,
    PaginatedPackageReviewResponse,
)
from app.services.package_service import PackageService
from app.users import current_admin_user

router = APIRouter(prefix="/admin/packages", tags=["Admin Package Review"])


@router.get("/pending", response_model=PaginatedPackageReviewResponse)
async def list_packages_pending_admin_review(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await PackageService(db).list_pending_admin_reviews(
        admin, page, page_size
    )


@router.patch(
    "/{package_id}/review",
    response_model=PackageDetailRead,
    status_code=status.HTTP_200_OK,
)
async def review_package(
    package_id: uuid.UUID,
    payload: PackageAdminReview,
    admin: User = Depends(current_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = PackageService(db)
    package = await service.admin_review_package(admin, package_id, payload)
    return await service.get_package_details(user=admin, package_id=package.id)
