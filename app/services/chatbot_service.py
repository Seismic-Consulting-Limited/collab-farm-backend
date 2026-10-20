import os
import logging
import httpx
from fastapi import HTTPException, status
from dotenv import load_dotenv

from app.models.user_model import User
from app.schemas.chatbot_schema import ChatRequest, ChatResponse

load_dotenv()

logger = logging.getLogger(__name__)

# Upstream URL and Service Key configuration
CHAT_BOT_URL = os.getenv("CHAT_BOT_URL", "https://collab-farm-ai-jymt.onrender.com/chat").rstrip("/")
SERVICE_KEY = os.getenv("SERVICE_KEY") or os.getenv("CHAT_SERVICE_KEY") or os.getenv("CHAT_API_KEY")

TARGET_ENDPOINT = CHAT_BOT_URL if CHAT_BOT_URL.endswith("/chat") else f"{CHAT_BOT_URL}/chat"

# Granular HTTPX Timeout configuration allowing cold-start buffer for Render
HTTPX_TIMEOUT = httpx.Timeout(
    connect=30.0,  # 30s to establish TCP connection (allows Render cold-start)
    read=90.0,     # 90s to read full AI response generated
    write=30.0,
    pool=30.0
)


class ChatService:
    async def send_message(self, user: User, payload: ChatRequest) -> ChatResponse:
        if not SERVICE_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chat assistant Service Key (SERVICE_KEY) is missing from environment configuration.",
            )

        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": SERVICE_KEY,
        }

        request_body = {
            "session_id": payload.session_id,
            "message": payload.message,
        }

        try:
            async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
                response = await client.post(
                    TARGET_ENDPOINT,
                    headers=headers,
                    json=request_body,
                )

            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                return ChatResponse(answer=data.get("answer", ""))

            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                key_preview = f"{SERVICE_KEY[:4]}***" if SERVICE_KEY else "None"
                logger.error(f"[ChatService 401] Upstream rejected Service Key starting with '{key_preview}'")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Upstream chatbot rejected the Service Key. Check SERVICE_KEY in environment variables.",
                )

            elif response.status_code == status.HTTP_404_NOT_FOUND:
                logger.error(f"[ChatService 404] Endpoint not found at {TARGET_ENDPOINT}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Upstream chatbot endpoint not found at '{TARGET_ENDPOINT}'.",
                )

            elif response.status_code == 422:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request payload sent to assistant.",
                )

            elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again shortly.",
                )

            else:
                logger.error(f"[ChatService Error] Upstream status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Upstream chatbot service returned HTTP {response.status_code}: {response.text}",
                )

        except httpx.ConnectTimeout:
            logger.warning(f"[ChatService ConnectTimeout] Render instance at {TARGET_ENDPOINT} is spinning up from cold-start.")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="The AI assistant service is spinning up from cold-start. Please send your request again in 20-30 seconds.",
            )
        except httpx.ReadTimeout:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="The assistant took too long to generate a response. Please try again shortly.",
            )
        except httpx.RequestError as exc:
            logger.error(f"[ChatService Connection Error] Failed to reach {TARGET_ENDPOINT}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to Chatbot microservice at {TARGET_ENDPOINT}. Error: {str(exc)}",
            )