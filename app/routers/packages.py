# app/routers/packages.py
import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session
from app.models.user import User
from app.schemas.package import PackageCreate, PackageStatus, PackageRead, PaginatedPackageResponse
from app.models.packages import InvestmentPackage, PackageStatus, TrancheType
from app.users import current_verified_investor, current_active_user

router = APIRouter(prefix="/packages", tags=["Investment Packages"])


@router.post("/create-package", response_model=PackageRead, status_code=status.HTTP_201_CREATED)
async def create_package(
    payload: PackageCreate,
    user: User = Depends(current_verified_investor),
    session: AsyncSession = Depends(get_async_session),
):
    package = InvestmentPackage(
        **payload.model_dump(),
        creator_id=user.id,
        status=PackageStatus.PENDING,
    )
    session.add(package)
    await session.commit()
    await session.refresh(package)
    return package


@router.get("/get-packages", response_model=PaginatedPackageResponse)
async def get_investor_packages(
    search: Optional[str] = Query(
        None, description="Search by package name or description"
    ),
    status_filter: Optional[PackageStatus] = Query(None, alias="status"),
    tranche_filter: Optional[TrancheType] = Query(None, alias="tranche"),
    sort_by: str = Query("newest", pattern="^(newest|oldest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    user: User = Depends(current_verified_investor),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(InvestmentPackage).where(
        InvestmentPackage.creator_id == user.id)

    if search:
        query = query.where(
            InvestmentPackage.title.ilike(f"%{search}%")
            | InvestmentPackage.description.ilike(f"%{search}%")
        )

    if status_filter:
        query = query.where(InvestmentPackage.status == status_filter)
    if tranche_filter:
        query = query.where(InvestmentPackage.tranche_type == tranche_filter)

    if sort_by == "newest":
        query = query.order_by(InvestmentPackage.created_at.desc())
    else:
        query = query.order_by(InvestmentPackage.created_at.asc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    packages = result.scalars().all()

    return PaginatedPackageResponse(
        items=packages,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/get-package-by-{package_id}", response_model=PackageRead)
async def get_package_by_id(
    package_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    package = await session.get(InvestmentPackage, package_id)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investment package with ID '{package_id}' not found.",
        )

    return package
