from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.userModel import User
from app.schemas.dashboard_schema import CooperativeDashboardResponse
from app.service.dashboard_service import DashboardService
from app.users import current_active_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get(
    "/overview",
    response_model=CooperativeDashboardResponse,
    status_code=status.HTTP_200_OK,
)
async def get_dashboard_overview(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await DashboardService(db).get_cooperative_dashboard(user=user)
