import os
import uuid
from decimal import Decimal
from typing import List, Optional
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user_model import User, UserRole
from app.models.wallet_model import (
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
)
from app.schemas.wallet_schema import (
    FundWalletSchema,
    ResolveAccountRequestSchema,
    WithdrawalRequestSchema,
)
from app.utils.paystack import (
    create_transfer_recipient,
    initiate_paystack_transfer,
    resolve_account_number,
)

load_dotenv()


class WalletService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _verify_investor_role(self, user: User) -> None:
        if user.role != UserRole.INVESTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only registered investors can access investor wallet operations.",
            )

    async def _get_or_create_wallet(self, user_id: uuid.UUID) -> Wallet:
        result = await self.session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = result.scalars().first()

        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                available_balance=0.0,
                locked_funds=0.0,
                actively_distributed=0.0,
            )
            self.session.add(wallet)
            await self.session.commit()
            await self.session.refresh(wallet)

        return wallet

    async def resolve_bank_account(
        self, user: User, payload: ResolveAccountRequestSchema
    ) -> dict:
        self._verify_investor_role(user)
        account_data = await resolve_account_number(
            account_number=payload.account_number,
            bank_code=payload.bank_code,
        )
        return {
            "account_number": account_data.get("account_number", payload.account_number),
            "account_name": account_data.get("account_name"),
            "bank_code": payload.bank_code,
        }

    async def initialize_funding(
        self, user: User, payload: FundWalletSchema
    ) -> dict:
        self._verify_investor_role(user)
        reference = f"WALLET_FUND_{uuid.uuid4().hex[:12]}"
        amount_in_kobo = int(payload.amount * 100)

        secret_key = os.getenv("PAYSTACK_SECRET_KEY")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {secret_key}"},
                json={
                    "email": user.email,
                    "amount": amount_in_kobo,
                    "reference": reference,
                    "callback_url": "/",
                },
            )

        paystack_data = response.json()
        if not paystack_data.get("status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not initialize payment with Paystack.",
            )

        wallet = await self._get_or_create_wallet(user.id)

        tx = Transaction(
            wallet_id=wallet.id,
            reference=reference,
            amount=payload.amount,
            description="Wallet Deposit via Paystack",
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.PENDING,
        )
        self.session.add(tx)
        await self.session.commit()

        return {
            "checkout_url": paystack_data["data"]["authorization_url"],
            "reference": reference,
        }

    async def verify_funding(self, user: User, reference: str) -> dict:
        self._verify_investor_role(user)
        secret_key = os.getenv("PAYSTACK_SECRET_KEY")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {secret_key}"},
            )

        paystack_data = response.json()
        if (
            not paystack_data.get("status")
            or paystack_data["data"]["status"] != "success"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction verification failed or unpaid.",
            )

        tx_result = await self.session.execute(
            select(Transaction).where(Transaction.reference == reference)
        )
        tx = tx_result.scalars().first()

        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction reference not found.",
            )

        wallet_result = await self.session.execute(
            select(Wallet).where(Wallet.id == tx.wallet_id)
        )
        wallet = wallet_result.scalars().first()

        if tx.status == TransactionStatus.PENDING:
            tx.status = TransactionStatus.COMPLETED

            if wallet:
                wallet.available_balance += Decimal(str(tx.amount))

            await self.session.commit()
            if wallet:
                await self.session.refresh(wallet)

        return {
            "status": "success",
            "message": "Payment verified and wallet credited.",
            "amount": tx.amount,
        }

    async def get_overview(self, user: User) -> Wallet:
        self._verify_investor_role(user)
        return await self._get_or_create_wallet(user.id)

    async def get_transactions(
        self,
        user: User,
        crop_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Transaction]:
        self._verify_investor_role(user)
        result = await self.session.execute(
            select(Wallet).where(Wallet.user_id == user.id)
        )
        wallet = result.scalars().first()

        if not wallet:
            return []

        query = select(Transaction).where(Transaction.wallet_id == wallet.id)

        if crop_type and crop_type.strip():
            query = query.where(
                Transaction.description.ilike(f"%{crop_type.strip()}%")
            )

        query = (
            query.order_by(Transaction.created_at.desc().nulls_last())
            .offset(offset)
            .limit(limit)
        )

        tx_result = await self.session.execute(query)
        return tx_result.scalars().all()

    
    async def withdraw_funds(
        self, user: User, payload: WithdrawalRequestSchema
    ) -> dict:
        self._verify_investor_role(user)
        result = await self.session.execute(
            select(Wallet).where(Wallet.user_id == user.id)
        )
        wallet = result.scalars().first()

        withdrawal_amount = Decimal(str(payload.amount))

        if not wallet or wallet.available_balance < withdrawal_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient wallet balance for this withdrawal.",
            )

        # 1. Derive verified account holder name directly from Paystack
        resolved_account = await resolve_account_number(
            account_number=payload.account_number,
            bank_code=payload.bank_code,
        )
        verified_account_name = resolved_account["account_name"]

        # 2. Create Transfer Recipient
        amount_in_kobo = int(withdrawal_amount * 100)
        recipient_code = await create_transfer_recipient(
            name=verified_account_name,
            account_number=payload.account_number,
            bank_code=payload.bank_code,
        )

        # 3. Trigger Transfer
        transfer_data = await initiate_paystack_transfer(
            amount_kobo=amount_in_kobo, recipient_code=recipient_code
        )

        # 4. Deduct Balance & Record Transaction
        wallet.available_balance -= withdrawal_amount
        is_success = transfer_data.get("status") in ["success", "pending"]

        transaction = Transaction(
            wallet_id=wallet.id,
            amount=withdrawal_amount,
            description=f"Withdrawal to {payload.account_number} ({verified_account_name})",
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED
            if is_success
            else TransactionStatus.FAILED,
            reference=transfer_data.get("transfer_code")
            or f"TRF-{uuid.uuid4().hex[:10]}",
        )

        self.session.add(transaction)
        await self.session.commit()

        return {
            "status": "success",
            "message": "Withdrawal processed successfully.",
            "new_balance": wallet.available_balance,
            "reference": transaction.reference,
        }