from fastapi import HTTPException, status

from app.models.user_model import User
from app.schemas.support_schema import SupportRequestCreate
from app.utils.emails import send_support_request_email


class SupportService:
    @staticmethod
    async def submit_request(user: User, payload: SupportRequestCreate) -> dict[str, str]:
        try:
            await send_support_request_email(
                topic=payload.topic.value.replace("_", " ").title(),
                subject=payload.subject,
                message=payload.message,
                reply_to=str(payload.reply_to),
                requester_name=user.full_name,
                requester_role=str(getattr(user.role, "value", user.role)),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The support email could not be sent. Please try again later.",
            ) from exc

        return {"message": "Your support request was sent to CollabFarm."}
