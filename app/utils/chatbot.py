# import os
# import httpx
# from fastapi import HTTPException, status

# AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")
# AI_SERVICE_API_KEY = os.getenv("AI_SERVICE_API_KEY",)


# async def forward_to_ai_service(user_message: str, conversation_id: str | None, user_id: str) -> dict:
#     payload = {
#         "user_id": str(user_id),
#         "conversation_id": conversation_id,
#         "message": user_message
#     }

#     headers = {
#         "Authorization": f"Bearer {AI_SERVICE_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     async with httpx.AsyncClient(timeout=30.0) as client:
#         try:
#             response = await client.post(AI_SERVICE_URL, json=payload, headers=headers)
#             response.raise_for_status()
#             return response.json()
#         except httpx.HTTPStatusError as e:
#             raise HTTPException(
#                 status_code=e.response.status_code,
#                 detail=f"AI Chatbot service error: {e.response.text}"
#             )
#         except httpx.RequestError:
#             raise HTTPException(
#                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#                 detail="AI Chatbot service is currently unreachable."
#             )
