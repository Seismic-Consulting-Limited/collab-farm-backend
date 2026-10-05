import httpx


AI_URL = "https://mp60cd2ef086206279f5.free.beeceptor.com/chat"


async def ask_ai(message: str) -> str:

    async with httpx.AsyncClient(timeout=30.0) as client:

        response = await client.post(
            AI_URL,
            json={
                "message": message
            }
        )

        print("AI STATUS:", response.status_code)
        print("AI HEADERS:", response.headers)
        print("AI RESPONSE:", repr(response.text))

        response.raise_for_status()

        return response.text
    
    