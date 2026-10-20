import traceback
from fastapi import APIRouter, Depends, HTTPException, status

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

    try:
        return await ChatService().send_message(user=user, payload=payload)
    except Exception as e:
        print("\n" + "=" * 20 + " CHATBOT ERROR TRACEBACK " + "=" * 20)
        traceback.print_exc()
        print("=" * 65 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chatbot execution error: {str(e)}"
        )