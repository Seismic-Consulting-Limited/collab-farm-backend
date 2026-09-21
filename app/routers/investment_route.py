import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.investment_schema import (
    CooperativeInvestmentDetail,
    CooperativeInvestmentSummary,
    InvestmentStatus,
    PaginatedCooperativeInvestments,
)
from app.services.investment_service import CooperativeInvestmentService
from app.users import current_active_user

router = APIRouter(prefix="/cooperative/investments",
                   tags=["Cooperative Investments"])


@router.get("/summary", response_model=CooperativeInvestmentSummary)
async def get_summary(
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CooperativeInvestmentService(db)
    return await service.get_dashboard_summary(cooperative_id=current_user.id)


@router.get("", response_model=PaginatedCooperativeInvestments)
async def list_investments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(
        None),
    category: str | None = Query(
        None),
    status_filter: InvestmentStatus | None = Query(None, alias="status"),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CooperativeInvestmentService(db)
    return await service.get_cooperative_investments(
        cooperative_id=current_user.id,
        page=page,
        size=size,
        search=search,
        category=category,
        status_filter=status_filter,
    )


@router.get("/{investment_id}", response_model=CooperativeInvestmentDetail)
async def get_investment_detail(
    investment_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = CooperativeInvestmentService(db)
    return await service.get_investment_detail(
        investment_id=investment_id,
        cooperative_id=current_user.id,
    )
