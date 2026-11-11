from fastapi import APIRouter, Depends, status

from app.models.user_model import User
from app.schemas.support_schema import (
    SupportRequestCreate,
    SupportRequestResponse,
    SupportTopic,
)
from app.services.support_service import SupportService
from app.users import current_active_user


router = APIRouter(prefix="/support", tags=["Support"])


@router.get("/topics", response_model=list[dict[str, str]])
async def list_support_topics(user: User = Depends(current_active_user)):
    return [
        {"value": topic.value, "label": topic.value.replace("_", " ").title()}
        for topic in SupportTopic
    ]


@router.post(
    "/contact",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def contact_support(
    payload: SupportRequestCreate,
    user: User = Depends(current_active_user),
):
    return await SupportService.submit_request(user, payload)
