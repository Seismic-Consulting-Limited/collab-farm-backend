import uuid
import httpx
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import get_async_session
from app.models.userModel import User
from app.models.walletModel import Wallet, Transaction, TransactionType, TransactionStatus
from app.schemas.walletSchema import WalletOverviewResponse, TransactionRead, FundWalletSchema
from app.users import current_active_user
from dotenv import load_dotenv
from decimal import Decimal


router = APIRouter(prefix="/wallet", tags=["Investors Wallet"])

load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")


@router.post("/fund/initialize")
async def initialize_wallet_funding(
    payload: FundWalletSchema,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    reference = f"WALLET_FUND_{uuid.uuid4().hex[:12]}"
    amount_in_kobo = int(payload.amount * 100)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.paystack.co/transaction/initialize",
            headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"},
            json={
                "email": user.email,
                "amount": amount_in_kobo,
                "reference": reference,
                "callback_url": "/"
            }
        )

    paystack_data = response.json()
    if not paystack_data.get("status"):
        raise HTTPException(
            status_code=400, detail="Could not initialize payment with Paystack.")

    result = await session.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()
    if not wallet:
        wallet = Wallet(user_id=user.id, available_balance=0.0,
                        locked_funds=0.0, actively_distributed=0.0)
        session.add(wallet)
        await session.flush()

    tx = Transaction(
        wallet_id=wallet.id,
        reference=reference,
        amount=payload.amount,
        description="Wallet Deposit via Paystack",
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.PENDING
    )
    session.add(tx)
    await session.commit()

    return {
        "checkout_url": paystack_data["data"]["authorization_url"],
        "reference": reference
    }


@router.get("/verify/{reference}")
async def verify_wallet_funding(
    reference: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        )

    paystack_data = response.json()
    if not paystack_data.get("status") or paystack_data["data"]["status"] != "success":
        raise HTTPException(
            status_code=400, detail="Transaction verification failed or unpaid.")

    tx_result = await session.execute(select(Transaction).where(Transaction.reference == reference))
    tx = tx_result.scalars().first()

    if not tx:
        raise HTTPException(
            status_code=404, detail="Transaction reference not found.")

    if tx.status == TransactionStatus.PENDING:
        tx.status = TransactionStatus.COMPLETED

        wallet_result = await session.execute(select(Wallet).where(Wallet.id == tx.wallet_id))
        wallet = wallet_result.scalars().first()
        if wallet:
            wallet.available_balance += Decimal(str(tx.amount))

        await session.commit()
        await session.refresh(wallet)

    return {
        "status": "success",
        "message": "Payment verified and wallet credited.",
        "amount": tx.amount
    }


@router.get("/overview", response_model=WalletOverviewResponse)
async def get_wallet_overview(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()

    if not wallet:
        wallet = Wallet(user_id=user.id, available_balance=0.0,
                        locked_funds=0.0, actively_distributed=0.0)
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)

    return wallet


@router.get("/transactions", response_model=List[TransactionRead])
async def get_wallet_transactions(
    crop_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()

    if not wallet:
        return []

    query = select(Transaction).where(Transaction.wallet_id == wallet.id)

    if crop_type and crop_type.strip():
        query = query.where(
            Transaction.description.ilike(f"%{crop_type.strip()}%"))

    query = query.order_by(Transaction.created_at.desc(
    ).nulls_last()).offset(offset).limit(limit)

    tx_result = await session.execute(query)
    return tx_result.scalars().all()
