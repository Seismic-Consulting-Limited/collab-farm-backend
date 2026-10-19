import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.wallet_model import TransactionStatus, TransactionType


class WalletOverviewResponse(BaseModel):
    available_balance: float
    locked_funds: float
    actively_distributed: float

    model_config = ConfigDict(from_attributes=True)


class TransactionRead(BaseModel):
    id: uuid.UUID
    reference: str
    amount: float
    description: str
    type: TransactionType
    status: TransactionStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FundWalletSchema(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in NGN")


class ResolveAccountRequestSchema(BaseModel):
    account_number: str = Field(..., min_length=10, max_length=10, description="10-digit NUBAN account number")
    bank_code: str = Field(..., min_length=3, description="Paystack bank code")


class ResolveAccountResponseSchema(BaseModel):
    account_number: str
    account_name: str
    bank_code: str


class WithdrawalRequestSchema(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount in NGN to withdraw")
    bank_code: str = Field(..., min_length=3, description="Paystack bank code")
    account_number: str = Field(..., min_length=10, max_length=10, description="10-digit NUBAN account number")
    account_name: str = Field(..., min_length=2, description="Account holder name")


class WithdrawalResponseSchema(BaseModel):
    status: str
    message: str
    new_balance: Decimal
    reference: str