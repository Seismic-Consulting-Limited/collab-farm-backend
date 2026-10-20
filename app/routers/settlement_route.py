import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.settlement_model import SettlementStatus
from app.models.user_model import User
from app.schemas.settlement_schema import (
    SettlementDetailResponse,
    SettlementMetricsResponse,
    SettlementPaginatedResponse,
    SettlementStatusUpdateSchema,
)
from app.services.settlement_service import SettlementService
from app.users import current_active_user

router = APIRouter(prefix="/settlements", tags=["Settlements Management"])


@router.get(
    "/metrics",
    response_model=SettlementMetricsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_settlement_metrics(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await SettlementService(session).get_metrics()


@router.get(
    "",
    response_model=SettlementPaginatedResponse,
    status_code=status.HTTP_200_OK,
)
async def list_settlements(
    search: Optional[str] = Query(
        None, description="Search farmer, package title, or reference"),
    package_type: Optional[str] = Query(
        None, description="Filter by package category"),
    status: Optional[SettlementStatus] = Query(
        None, description="Filter by settlement status"),
    start_date: Optional[datetime] = Query(
        None, description="Filter start date"),
    end_date: Optional[datetime] = Query(None, description="Filter end date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    items, total = await SettlementService(session).get_settlements(
        search=search,
        package_type=package_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return SettlementPaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/{settlement_id}",
    response_model=SettlementDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_settlement_detail(
    settlement_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await SettlementService(session).get_settlement_detail(settlement_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{settlement_id}/status",
    status_code=status.HTTP_200_OK,
)
async def update_settlement_status(
    settlement_id: uuid.UUID,
    payload: SettlementStatusUpdateSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        updated = await SettlementService(session).update_status(settlement_id, payload)
        return {"status": "success", "new_status": updated.status}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
