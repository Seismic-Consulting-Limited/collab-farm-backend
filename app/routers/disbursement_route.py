import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.disbursement_model import DisbursementStatus
from app.models.user_model import User
from app.schemas.disbursement_schema import (
    DisbursementDetailResponse,
    DisbursementMetricsResponse,
    DisbursementPaginatedResponse,
    DisbursementStatusUpdateSchema,
)
from app.services.disbursement_service import DisbursementService
from app.users import current_active_user

router = APIRouter(prefix="/disbursements", tags=["Disbursements Management"])


@router.get(
    "/metrics",
    response_model=DisbursementMetricsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_disbursement_metrics(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await DisbursementService(session).get_metrics(cooperative_id=user.id)


@router.get(
    "",
    response_model=DisbursementPaginatedResponse,
    status_code=status.HTTP_200_OK,
)
async def list_disbursements(
    search: Optional[str] = Query(
        None, description="Search farmer, package, or transaction reference"),
    package_type: Optional[str] = Query(
        None, description="Filter by package category"),
    status: Optional[DisbursementStatus] = Query(
        None, description="Filter by status"),
    start_date: Optional[datetime] = Query(
        None, description="Filter start date"),
    end_date: Optional[datetime] = Query(None, description="Filter end date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    items, total = await DisbursementService(session).get_disbursements(
        cooperative_id=user.id,
        search=search,
        package_type=package_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return DisbursementPaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/{disbursement_id}",
    response_model=DisbursementDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_disbursement_detail(
    disbursement_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await DisbursementService(session).get_disbursement_detail(
            disbursement_id=disbursement_id, cooperative_id=user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{disbursement_id}/status",
    status_code=status.HTTP_200_OK,
)
async def update_disbursement_status(
    disbursement_id: uuid.UUID,
    payload: DisbursementStatusUpdateSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):

    try:
        updated = await DisbursementService(session).update_status(
            disbursement_id=disbursement_id, payload=payload, admin_user=user
        )
        return {
            "status": "success",
            "message": f"Disbursement status updated to {updated.status}",
            "new_status": updated.status,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
