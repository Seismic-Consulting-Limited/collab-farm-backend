# from fastapi import APIRouter, Depends
# from app.models.userModel import User
# from app.users import current_active_user
# from app.schemas.chatSchema import ChatRequestSchema, ChatResponseSchema
# from app.utils.chatbot import forward_to_ai_service

# router = APIRouter(prefix="/chat", tags=["AI Chatbot"])


# @router.post("/", response_model=ChatResponseSchema)
# async def chat_bridge(
#     payload: ChatRequestSchema,
#     user: User = Depends(current_active_user)
# ):
#     return await forward_to_ai_service(
#         user_message=payload.message,
#         conversation_id=str(
#             payload.conversation_id) if payload.conversation_id else None,
#         user_id=str(user.id)
#     )
