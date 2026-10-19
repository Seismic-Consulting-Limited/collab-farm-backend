import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.disbursement_schema import (
    DisbursementDetailResponse,
    PaginatedDisbursementResponse,
)
from app.services.disbursement_service import DisbursementService
from app.users import current_active_user

router = APIRouter(
    prefix="/cooperative/disbursements", tags=["Cooperative Disbursements"]
)


@router.get(
    "",
    response_model=PaginatedDisbursementResponse,
    status_code=status.HTTP_200_OK,
)
async def get_disbursements_overview(
    search: Optional[str] = Query(None),
    package_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await DisbursementService(db).get_disbursements_overview(
        user=user,
        search=search,
        package_type=package_type,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{disbursement_id}",
    response_model=DisbursementDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_disbursement_detail(
    disbursement_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await DisbursementService(db).get_disbursement_detail(
        user=user, disbursement_id=disbursement_id
    )
