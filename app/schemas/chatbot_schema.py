from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Unique session UUID for conversation memory",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message prompt for the assistant",
    )


class ChatResponse(BaseModel):
    answer: str