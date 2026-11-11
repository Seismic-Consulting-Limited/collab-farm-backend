import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_model import Notification
from app.models.user_model import User
from app.schemas.notification_schema import NotificationInboxResponse


def add_notification(
    session: AsyncSession,
    recipient_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: str,
    *,
    actor_id: Optional[uuid.UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    link: Optional[str] = None,
) -> Notification:
    notification = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        title=title,
        message=message,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        link=link,
    )
    session.add(notification)
    return notification


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_notifications(
        self,
        user: User,
        is_read: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> NotificationInboxResponse:
        base = select(Notification).where(Notification.recipient_id == user.id)
        if is_read is not None:
            base = base.where(Notification.is_read == is_read)

        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        unread_count = await self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == user.id,
                Notification.is_read.is_(False),
            )
        )
        items = (
            await self.session.execute(
                base.order_by(Notification.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return NotificationInboxResponse(
            total=int(total or 0),
            unread_count=int(unread_count or 0),
            page=page,
            page_size=page_size,
            items=items,
        )

    async def mark_as_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        notification = (
            await self.session.execute(
                select(Notification).where(
                    Notification.id == notification_id,
                    Notification.recipient_id == user.id,
                )
            )
        ).scalars().first()
        if notification is None:
            raise HTTPException(status_code=404, detail="Notification not found.")
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(notification)
        return notification

    async def get_unread_count(self, user: User) -> int:
        count = await self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == user.id,
                Notification.is_read.is_(False),
            )
        )
        return int(count or 0)

    async def mark_all_as_read(self, user: User) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.recipient_id == user.id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.session.commit()
        return int(result.rowcount or 0)
