import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.walletModel import TransactionType, TransactionStatus
from decimal import Decimal


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


class WithdrawalRequestSchema(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount in NGN to withdraw")
    bank_code: str = Field(..., min_length=3,
                           description="Paystack 3-digit bank code")
    account_number: str = Field(..., min_length=10, max_length=10,
                                description="10-digit NUBAN account number")
    account_name: str = Field(..., min_length=2,
                              description="Account holder name")
