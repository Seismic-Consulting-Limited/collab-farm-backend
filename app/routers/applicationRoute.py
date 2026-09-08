import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from app.db import get_async_session
from app.models.userModel import User
from app.models.packageModel import InvestmentPackage, PackageStatus
from app.models.applicationModel import FundingApplication, ApplicationStatus
from app.schemas.applicationSchema import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdateSchema, PaginatedAplicationResponse, InvestorApplicationReviewSchema
)
from app.users import current_active_user

router = APIRouter(prefix="/applications", tags=["Funding Applications"])


@router.post("/create", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_funding_application(
    payload: ApplicationCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    package = await session.get(InvestmentPackage, payload.package_id)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target investment package not found.",
        )

    if package.status != PackageStatus.LIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot apply to a package that is not LIVE. Current status: '{package.status.value}'.",
        )

    if payload.requested_amount > Decimal(str(package.total_fund_amount)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested amount exceeds total package funding limit of {package.total_fund_amount}.",
        )

    disbursement_data = [t.model_dump(mode="json")
                         for t in payload.disbursement_plan]
    farmer_ids = [fid for fid in payload.target_farmer_ids]

    application = FundingApplication(
        package_id=payload.package_id,
        cooperative_id=user.id,
        requested_amount=payload.requested_amount,
        target_farmer_ids=farmer_ids,
        disbursement_plan=disbursement_data,
        notes=payload.notes,
        status=ApplicationStatus.PENDING_ADMIN,
    )

    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


@router.get("/my-applications", response_model=PaginatedAplicationResponse)
async def get_cooperative_applications(
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(FundingApplication).where(
        FundingApplication.cooperative_id == user.id)

    if status_filter:
        query = query.where(FundingApplication.status == status_filter)

    query = query.order_by(FundingApplication.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    applications = result.scalars().all()

    return PaginatedAplicationResponse(
        items=applications,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/package/{package_id}", response_model=PaginatedAplicationResponse)
async def get_applications_for_package(
    package_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    package = await session.get(InvestmentPackage, package_id)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investment package not found.",
        )

    if package.creator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view applications for this package.",
        )

    query = select(FundingApplication).where(
        FundingApplication.package_id == package_id
    ).order_by(FundingApplication.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    applications = result.scalars().all()

    return PaginatedAplicationResponse(
        items=applications,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application_by_id(
    application_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    application = await session.get(FundingApplication, application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funding application not found.",
        )

    return application


@router.put("/revise/{application_id}", response_model=ApplicationRead)
async def revise_funding_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdateSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(FundingApplication).where(
            FundingApplication.id == application_id,
            FundingApplication.cooperative_id == user.id,
        )
    )
    application = result.scalars().first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funding application not found or unauthorized.",
        )

    allowed_statuses = [
        ApplicationStatus.REVISION_REQUESTED,
        ApplicationStatus.DRAFT,
        ApplicationStatus.REJECTED,
    ]

    if application.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revise application in status '{application.status.value}'.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "disbursement_plan" in update_data and update_data["disbursement_plan"] is not None:
        update_data["disbursement_plan"] = [
            t.model_dump(mode="json") if hasattr(t, "model_dump") else t
            for t in update_data["disbursement_plan"]
        ]

    for field, value in update_data.items():
        setattr(application, field, value)

    application.status = ApplicationStatus.PENDING_ADMIN
    application.rejection_reason = None
    application.revision_note = None

    await session.commit()
    await session.refresh(application)
    return application


@router.patch("/investor-decision/{application_id}", response_model=ApplicationRead)
async def investor_application_decision(
    application_id: uuid.UUID,
    payload: InvestorApplicationReviewSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(FundingApplication)
        .join(InvestmentPackage, FundingApplication.package_id == InvestmentPackage.id)
        .where(
            FundingApplication.id == application_id,
            InvestmentPackage.creator_id == user.id
        )
    )
    application = result.scalars().first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funding application not found or does not belong to any of your investment packages."
        )

    if application.status != ApplicationStatus.PENDING_INVESTOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review application. Current status is '{application.status.value}', expected 'PENDING_INVESTOR'."
        )

    if payload.approved:
        application.status = ApplicationStatus.APPROVED
        application.rejection_reason = None
    else:
        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = payload.rejection_reason or "Application declined by investor."

    await session.commit()
    await session.refresh(application)
    return application
