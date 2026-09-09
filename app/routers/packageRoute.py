import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.packageModel import InvestmentPackage, PackageStatus, TrancheType
from app.models.userModel import User, UserRole
from app.schemas.packageschema import (
    AdminPackageReview,
    InvestorConfirmation,
    PackageCreate,
    PackageRead,
    PackageUpdate,
    PaginatedPackageResponse,
)
from app.users import current_active_user, current_verified_investor

router = APIRouter(prefix="/packages", tags=["Investment Packages"])


@router.post("", response_model=PackageRead, status_code=status.HTTP_201_CREATED)
async def create_package(
    payload: PackageCreate,
    user: User = Depends(current_verified_investor),
    session: AsyncSession = Depends(get_async_session),
):
    if user.role != UserRole.INVESTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only verified investors can create investment packages.",
        )

    package = InvestmentPackage(
        **payload.model_dump(),
        creator_id=user.id,
        status=PackageStatus.PENDING_ADMIN_REVIEW,
    )
    session.add(package)
    await session.commit()
    await session.refresh(package)
    return package


@router.get("", response_model=PaginatedPackageResponse)
async def get_investment_packages(
    search: Optional[str] = Query(None, description="Search by package name"),
    status_filter: Optional[PackageStatus] = Query(None, alias="status"),
    tranche_filter: Optional[TrancheType] = Query(None, alias="tranche"),
    sort_by: str = Query("newest", pattern="^(newest|oldest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(InvestmentPackage)

    if user.role == UserRole.INVESTOR:
        query = query.where(InvestmentPackage.creator_id == user.id)
    elif user.role == UserRole.COOPERATIVE:
        query = query.where(InvestmentPackage.status == PackageStatus.ACTIVE)

    if search:
        query = query.where(InvestmentPackage.name.ilike(f"%{search}%"))

    if status_filter and user.role != UserRole.COOPERATIVE:
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


@router.get("/{package_id}", response_model=PackageRead)
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

    if user.role == UserRole.COOPERATIVE and package.status != PackageStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cooperatives can only view active investment packages.",
        )

    return package


@router.patch("/revise/{package_id}", response_model=PackageRead)
async def revise_investment_package(
    package_id: uuid.UUID,
    payload: PackageUpdate,
    user: User = Depends(current_verified_investor),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(InvestmentPackage).where(
            InvestmentPackage.id == package_id,
            InvestmentPackage.creator_id == user.id,
        )
    )
    package = result.scalars().first()

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investment package not found or does not belong to you.",
        )

    if package.status not in [PackageStatus.PENDING_ADMIN_REVIEW, PackageStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revise package with status '{package.status.value}'.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(package, field, value)

    package.status = PackageStatus.PENDING_ADMIN_REVIEW
    package.rejection_reason = None

    await session.commit()
    await session.refresh(package)
    return package


@router.patch("/admin-review/{package_id}", response_model=PackageRead)
async def admin_review_package(
    package_id: uuid.UUID,
    payload: AdminPackageReview,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrator accounts can review investment packages.",
        )

    package = await session.get(InvestmentPackage, package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investment package with ID '{package_id}' not found.",
        )

    if payload.status not in [PackageStatus.PENDING_INVESTOR_CONFIRMATION, PackageStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin review status must be 'PENDING_INVESTOR_CONFIRMATION' or 'REJECTED'.",
        )

    update_data = payload.model_dump(exclude_unset=True, exclude={
                                     "status", "rejection_reason"})
    for field, value in update_data.items():
        setattr(package, field, value)

    package.status = payload.status
    if payload.rejection_reason:
        package.rejection_reason = payload.rejection_reason

    await session.commit()
    await session.refresh(package)
    return package


@router.patch("/final-decision/{package_id}", response_model=PackageRead)
async def investor_final_decision(
    package_id: uuid.UUID,
    payload: InvestorConfirmation,
    user: User = Depends(current_verified_investor),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(InvestmentPackage).where(
            InvestmentPackage.id == package_id,
            InvestmentPackage.creator_id == user.id,
        )
    )
    package = result.scalars().first()

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investment package not found or does not belong to you.",
        )

    if package.status != PackageStatus.PENDING_INVESTOR_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Package must be in 'PENDING_INVESTOR_CONFIRMATION' status. Current status: '{package.status.value}'.",
        )

    if payload.confirm:
        package.status = PackageStatus.ACTIVE
        package.rejection_reason = None
    else:
        package.status = PackageStatus.REJECTED
        package.rejection_reason = payload.rejection_reason or "Withdrawn by investor after admin review."

    await session.commit()
    await session.refresh(package)
    return package


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
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

    is_creator = package.creator_id == user.id
    is_admin = user.role == UserRole.ADMIN

    if not (is_creator or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this investment package.",
        )

    if is_creator and package.status == PackageStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active investment package.",
        )

    await session.delete(package)
    await session.commit()
    return None
