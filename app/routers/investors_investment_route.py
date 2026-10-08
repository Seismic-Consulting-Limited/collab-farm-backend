import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.investors_investment_schema import (
    InvestmentCreateRequest,
    InvestmentResponse,
    InvestorInvestmentDetailResponse,
    InvestorInvestmentsOverviewResponse,
)
from app.services.investors_investment_service import InvestmentService
from app.users import current_active_user

router = APIRouter(prefix="/investments", tags=["Investors Investments"])


@router.post(
    "",
    response_model=InvestmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_investment(
    payload: InvestmentCreateRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Deducts funds from investor wallet and creates a new investment entry.
    Rejects the request if the investor already has an active or pending investment in the same package.
    """
    return await InvestmentService(db).process_investment(
        investor_id=user.id, data=payload
    )


@router.get("", response_model=InvestorInvestmentsOverviewResponse)
async def get_my_investments(
    status: Optional[str] = Query(
        None, description="Filter by status e.g. ACTIVE, COMPLETED, OVERDUE"
    ),
    search: Optional[str] = Query(None, description="Search by package title"),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Returns summary statistics and the list of investment packages funded by the investor.
    """
    return await InvestmentService(db).get_investor_investments(
        investor_id=user.id,
        status_filter=status,
        search=search,
    )


@router.get("/{investment_id}", response_model=InvestorInvestmentDetailResponse)
async def get_investment_detail(
    investment_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Returns specific investment details including package progress and settlement info.
    """
    return await InvestmentService(db).get_investor_investment_detail(
        investor_id=user.id,
        investment_id=investment_id,
    )