import traceback
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user_model import User
from app.schemas.chatbot_schema import ChatRequest, ChatResponse
from app.services.chatbot_service import ChatService
from app.users import fastapi_users

optional_active_user = fastapi_users.current_user(active=True, optional=True)

router = APIRouter(prefix="/chat", tags=["AI Assistant Chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_assistant(
    payload: ChatRequest,
    user: Optional[User] = Depends(optional_active_user),
):
    try:
        return await ChatService().send_message(user=user, payload=payload)
    except HTTPException:
        # Re-raise standard HTTP exceptions so their true status codes (504, 401, etc.) are preserved
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected chatbot execution error: {str(exc)}",
        )