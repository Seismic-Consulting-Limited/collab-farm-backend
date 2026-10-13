import os
import httpx
from fastapi import HTTPException, status
from dotenv import load_dotenv

from app.models.user_model import User
from app.schemas.chatbot_schema import ChatRequest, ChatResponse

load_dotenv()

CHAT_BOT_URL = os.getenv("CHAT_BOT_URL", "http://192.168.88.225:8000")
CHAT_API_KEY = os.getenv("CHAT_API_KEY")


class ChatService:
    async def send_message(self, user: User, payload: ChatRequest) -> ChatResponse:
        if not CHAT_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chat assistant API key is missing from environment configuration.",
            )

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": CHAT_API_KEY,
            "X-Client-Id": str(user.id),  # Scopes the 20 msg/min rate limit to individual users
        }

        request_body = {
            "session_id": payload.session_id,
            "message": payload.message,
        }

        try:
            # 60-second timeout as specified in the guide
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{CHAT_BOT_URL.rstrip('/')}/chat",
                    headers=headers,
                    json=request_body,
                )

            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                return ChatResponse(answer=data.get("answer", ""))

            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing chatbot API key.",
                )

            elif response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid request format sent to assistant.",
                )

            elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again shortly.",
                )

            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="The assistant is unavailable right now. Please try again shortly.",
                )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="The assistant took too long to respond. Please try again shortly.",
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The assistant is unavailable right now. Please try again shortly.",
            )