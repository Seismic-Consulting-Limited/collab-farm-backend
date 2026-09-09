import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.applicationModel import FundingApplication, ApplicationStatus
from app.models.disbursementModel import DisbursementSchedule, DisbursementStatus
from app.models.packageModel import InvestmentPackage
from app.models.userModel import User
from app.schemas.disbursementSchema import (
    DisbursementReadSchema,
    DisbursementReleaseSchema,
    MilestoneSubmitSchema,
)
from app.users import current_active_user, current_verified_investor

router = APIRouter(prefix="/disbursements", tags=["Disbursements"])


@router.get("/application/{application_id}", response_model=List[DisbursementReadSchema])
async def get_application_disbursements(
    application_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(DisbursementSchedule)
        .where(DisbursementSchedule.application_id == application_id)
        .order_by(DisbursementSchedule.tranche_number.asc())
    )
    return result.scalars().all()


@router.patch("/submit-milestone/{disbursement_id}", response_model=DisbursementReadSchema)
async def submit_milestone_proof(
    disbursement_id: uuid.UUID,
    payload: MilestoneSubmitSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    disbursement = await session.get(DisbursementSchedule, disbursement_id)
    if not disbursement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disbursement tranche not found."
        )

    if disbursement.status == DisbursementStatus.DISBURSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tranche has already been disbursed."
        )

    disbursement.milestone_proof_url = payload.milestone_proof_url
    disbursement.status = DisbursementStatus.MILESTONE_SUBMITTED

    await session.commit()
    await session.refresh(disbursement)
    return disbursement


@router.patch("/disburse/{disbursement_id}", response_model=DisbursementReadSchema)
async def disburse_tranche_funds(
    disbursement_id: uuid.UUID,
    payload: DisbursementReleaseSchema,
    user: User = Depends(current_verified_investor),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(DisbursementSchedule, FundingApplication)
        .join(FundingApplication, DisbursementSchedule.application_id == FundingApplication.id)
        .join(InvestmentPackage, FundingApplication.package_id == InvestmentPackage.id)
        .where(
            DisbursementSchedule.id == disbursement_id,
            InvestmentPackage.creator_id == user.id
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disbursement record not found or package does not belong to you."
        )

    disbursement, application = row

    if application.status != ApplicationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disburse funds for an unapproved application."
        )

    if disbursement.status == DisbursementStatus.DISBURSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This tranche has already been disbursed."
        )

    disbursement.status = DisbursementStatus.DISBURSED
    disbursement.transaction_reference = payload.transaction_reference
    disbursement.disbursed_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(disbursement)
    return disbursement
