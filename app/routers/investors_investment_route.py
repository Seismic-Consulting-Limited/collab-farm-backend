import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.investors_investment_schema import (
    InvestmentCreateRequest,
    InvestmentProgressResponse,
    InvestmentResponse,
    InvestorInvestmentDetailResponse,
    InvestorInvestmentsOverviewResponse,
)
from app.services.investors_investment_service import InvestmentService
from app.users import current_active_user
from app.utils.dependencies import require_approved_investor

router = APIRouter(prefix="/investments", tags=["Investors Investments"], dependencies=[Depends(require_approved_investor)])


@router.post(
    "/{package_id}",
    response_model=InvestmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_investment(
    package_id: uuid.UUID,
    payload: InvestmentCreateRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await InvestmentService(db).process_investment(
        user=user, package_id=package_id, investment_amount=payload.amount
    )


@router.get("", response_model=InvestorInvestmentsOverviewResponse)
async def get_my_investments(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await InvestmentService(db).get_investor_investments(
        user=user, status_filter=status, search=search
    )


@router.get("/{investment_id}", response_model=InvestorInvestmentDetailResponse)
async def get_investment_detail(
    investment_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await InvestmentService(db).get_investor_investment_detail(
        user=user, investment_id=investment_id
    )


@router.get(
    "/{investment_id}/progress",
    response_model=InvestmentProgressResponse,
    status_code=status.HTTP_200_OK,
)
async def get_investment_progress(
    investment_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await InvestmentService(db).get_investor_investment_progress(
        user=user, investment_id=investment_id
    )
