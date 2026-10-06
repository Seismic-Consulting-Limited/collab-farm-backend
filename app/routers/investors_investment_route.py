from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.investors_investment_schema import InvestmentCreateRequest, InvestmentResponse
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
 
    return await InvestmentService(db).process_investment(investor_id=user.id, data=payload)