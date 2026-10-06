from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.investor_dashboard_schema import InvestorDashboardResponse
from app.services.investor_dashboard_service import InvestorDashboardService
from app.users import current_active_user

router = APIRouter(prefix="/investor", tags=["Investor Dashboard"])


@router.get(
    "/dashboard",
    response_model=InvestorDashboardResponse,
    status_code=status.HTTP_200_OK,
)
async def get_investor_dashboard(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
): 
    return await InvestorDashboardService(db).get_dashboard_data(investor_id=user.id)