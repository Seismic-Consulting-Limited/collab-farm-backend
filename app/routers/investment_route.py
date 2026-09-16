from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.userModel import User
from app.schemas.investment_schema import PaginatedInvestmentsResponse
from app.service.investment_service import InvestmentService
from app.users import current_active_user

router = APIRouter(prefix="/investments", tags=["Investments Management"])


@router.get(
    "/",
    response_model=PaginatedInvestmentsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_cooperative_investments(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await InvestmentService(db).get_cooperative_investments(
        user=user, page=page, limit=limit
    )