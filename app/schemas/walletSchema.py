import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.walletModel import TransactionType, TransactionStatus

class WalletOverviewResponse(BaseModel):
    available_balance: float
    locked_funds: float
    actively_distributed: float

    class Config:
        from_attributes = True

class TransactionRead(BaseModel):
    id: uuid.UUID
    reference: str
    amount: float
    description: str
    type: TransactionType
    status: TransactionStatus
    created_at: datetime

    class Config:
        from_attributes = True
        
class FundWalletSchema(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in Naira")