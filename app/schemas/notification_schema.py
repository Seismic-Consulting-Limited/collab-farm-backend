import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    notification_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    link: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationInboxResponse(BaseModel):
    total: int
    unread_count: int
    page: int
    page_size: int
    items: list[NotificationRead]


class MarkAllReadResponse(BaseModel):
    updated_count: int
    message: str
