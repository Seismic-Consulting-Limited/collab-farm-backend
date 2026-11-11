from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class SupportTopic(str, Enum):
    ACCOUNT = "ACCOUNT"
    INVESTMENTS = "INVESTMENTS"
    PACKAGES = "PACKAGES"
    PAYMENTS = "PAYMENTS"
    FARMERS = "FARMERS"
    TECHNICAL = "TECHNICAL"
    OTHER = "OTHER"


class SupportRequestCreate(BaseModel):
    topic: SupportTopic
    subject: str = Field(..., min_length=2, max_length=160)
    message: str = Field(..., min_length=1, max_length=1000)
    reply_to: EmailStr

    @field_validator("subject", "message")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("subject")
    @classmethod
    def reject_subject_line_breaks(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("Subject must be a single line.")
        return value


class SupportRequestResponse(BaseModel):
    message: str
