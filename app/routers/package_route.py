import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session
from app.models.user_model import User
from app.schemas.package_schema import AssignFarmerSchema, PackageCreate, PackageDetailRead, PackageInvestorResponse, PackageRead, PackageUpdate
from app.models.package_model import PackageStatus, PackageType, PackageCategory
from typing import Optional
from app.services.package_service import PackageService
from app.users import current_active_user

router = APIRouter(prefix="/packages", tags=["Funding Packages"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_package(
    payload: PackageCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await PackageService(db).create_package(user=user, payload=payload)


@router.post("/{package_id}/assign-farmer", status_code=status.HTTP_201_CREATED)
async def assign_farmer_to_package(
    package_id: uuid.UUID,
    payload: AssignFarmerSchema,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await PackageService(db).assign_farmer(
        user=user, package_id=package_id, payload=payload
    )


@router.get("/{package_id}", response_model=PackageDetailRead, status_code=status.HTTP_200_OK)
async def get_package_detail(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await PackageService(db).get_package_details(package_id=package_id)


# @router.get(
#     "/{package_id}/investors",
#     response_model=list[PackageInvestorResponse],
#     status_code=status.HTTP_200_OK,
# )
# async def get_package_investors(
#     package_id: uuid.UUID,
#     db: AsyncSession = Depends(get_async_session),
# ):
#     return await PackageService(db).get_package_investors(package_id=package_id)


@router.get("/", response_model=list[PackageRead], status_code=status.HTTP_200_OK)
async def get_all_packages(
    category: Optional[PackageCategory] = None,
    package_type: Optional[PackageType] = None,
    status_filter: Optional[PackageStatus] = None,
    cooperative_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_async_session),
):
    return await PackageService(db).get_all_packages(
        category=category,
        package_type=package_type,
        status_filter=status_filter,
        cooperative_id=cooperative_id,
    )


@router.patch("/{package_id}", response_model=PackageRead, status_code=status.HTTP_200_OK)
async def update_package(
    package_id: uuid.UUID,
    payload: PackageUpdate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await PackageService(db).update_package(
        user=user, package_id=package_id, payload=payload
    )
