from fastapi import APIRouter, HTTPException
import httpx
from app.schemas.chatbot_schema import ChatRequest, ChatResponse
from app.services.chatbot_service import ask_ai


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:
        response = await ask_ai(request.message)

        return ChatResponse(
            response=response
        )

    except httpx.HTTPStatusError as e:
        print("AI HTTP ERROR:", e)

        raise HTTPException(
            status_code=502,
            detail="AI service returned an error"
        )

    except Exception as e:
        print("CHAT ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )