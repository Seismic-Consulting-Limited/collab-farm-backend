from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.dependencies import require_approved_investor
from app.db import get_async_session
from app.models.user_model import User
from app.schemas.investor_dashboard_schema import (
    InvestorCooperativesResponse,
    InvestorDashboardResponse,
)
from app.services.investor_dashboard_service import InvestorDashboardService
from app.services.investor_cooperative_service import InvestorCooperativeService
from app.users import current_active_user

router = APIRouter(prefix="/investor", tags=["Investor Dashboard"], dependencies=[Depends(require_approved_investor)])

# def verify_investor_access(user: User = Depends(current_active_user)) -> User:
#     """Ensure the authenticated user is an investor, allowing all investor sub-types."""
#     user_role = str(getattr(user, "role", "")).upper()
    
#     if "INVESTOR" not in user_role:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Access denied. Only registered investors can access this dashboard.",
#         )
#     return user

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


@router.get(
    "/cooperatives",
    response_model=InvestorCooperativesResponse,
    status_code=status.HTTP_200_OK,
)
async def list_investor_cooperatives(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    return await InvestorCooperativeService(db).list_cooperatives(
        page=page, page_size=page_size
    )
