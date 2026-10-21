from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.user_model import User
from app.schemas.wallet_schema import (
    FundWalletSchema,
    ResolveAccountRequestSchema,
    ResolveAccountResponseSchema,
    TransactionRead,
    WalletOverviewResponse,
    WithdrawalRequestSchema,
    WithdrawalResponseSchema,
)
from app.services.wallet_service import WalletService
from app.users import current_active_user
from app.utils.dependencies import require_approved_investor

router = APIRouter(prefix="/wallet", tags=["Investors Wallet"], dependencies=[Depends(require_approved_investor)])


@router.post(
    "/resolve-account",
    response_model=ResolveAccountResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def resolve_bank_account(
    payload: ResolveAccountRequestSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await WalletService(session).resolve_bank_account(
        user=user, payload=payload
    )


@router.post("/fund/initialize", status_code=status.HTTP_200_OK)
async def initialize_wallet_funding(
    payload: FundWalletSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await WalletService(session).initialize_funding(
        user=user, payload=payload
    )


@router.get("/verify/{reference}", status_code=status.HTTP_200_OK)
async def verify_wallet_funding(
    reference: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await WalletService(session).verify_funding(
        user=user, reference=reference
    )


@router.get("/overview", response_model=WalletOverviewResponse)
async def get_wallet_overview(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await WalletService(session).get_overview(user=user)


@router.get("/transactions", response_model=List[TransactionRead])
async def get_wallet_transactions(
    crop_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await WalletService(session).get_transactions(
        user=user, crop_type=crop_type, limit=limit, offset=offset
    )


@router.post(
    "/withdraw",
    response_model=WithdrawalResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def withdraw_funds(
    payload: WithdrawalRequestSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await WalletService(session).withdraw_funds(
        user=user, payload=payload
    )
