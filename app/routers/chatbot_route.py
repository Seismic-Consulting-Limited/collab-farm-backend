from fastapi import APIRouter, Depends, status

from app.models.user_model import User
from app.schemas.chatbot_schema import ChatRequest, ChatResponse
from app.services.chatbot_service import ChatService
from app.users import current_active_user

router = APIRouter(prefix="/chat", tags=["AI Assistant Chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_assistant(
    payload: ChatRequest,
    user: User = Depends(current_active_user),
):
    """
    Proxy endpoint for talking to the CollabFarm AI Assistant.
    Requires an authenticated active user context.
    """
    return await ChatService().send_message(user=user, payload=payload)