import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.notification_schema import (
    MarkAllReadResponse,
    NotificationInboxResponse,
    NotificationRead,
)
from app.services.notification_service import NotificationService
from app.users import current_active_user


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/unread-count", response_model=dict[str, int])
async def get_unread_notification_count(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return {"unread_count": await NotificationService(session).get_unread_count(user)}


@router.get("", response_model=NotificationInboxResponse)
async def list_notifications(
    is_read: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await NotificationService(session).list_notifications(
        user=user, is_read=is_read, page=page, page_size=page_size
    )


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_notifications_as_read(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    updated_count = await NotificationService(session).mark_all_as_read(user)
    return MarkAllReadResponse(
        updated_count=updated_count,
        message="All notifications have been marked as read.",
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await NotificationService(session).mark_as_read(user, notification_id)
