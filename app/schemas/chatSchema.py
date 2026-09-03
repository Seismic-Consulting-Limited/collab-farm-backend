# from pydantic import BaseModel, Field
# from typing import Optional, List
# import uuid

# class ChatMessage(BaseModel):
#     role: str = Field(..., description="user, assistant, or system")
#     content: str
    
# class ChatRequestSchema(BaseModel):
#     message: str = Field(..., min_length=1, description="Users Response")
#     conversion_id: Optional[uuid.UUID] = None
    
    
# class ChatResponseSchema(BaseModel):
#     reply: str
#     conversion_id: uuid.UUID