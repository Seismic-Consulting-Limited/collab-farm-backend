import uuid
from datetime import datetime, time, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investment_model import Investment, InvestmentStatus
from app.models.package_model import Package
from app.models.wallet_model import (
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
)
from app.schemas.investors_investment_schema import InvestmentCreateRequest, InvestmentResponse


class InvestmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_package_roi(self, package: Package) -> float:
        """Extract expected ROI percentage from package."""
        val = getattr(package, "expected_roi", None)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return 0.0

    def _get_payback_date(self, package: Package) -> Optional[datetime]:
        """Extract expected payback date from package and convert to datetime."""
        payback_date = getattr(package, "expected_payback_date", None)
        if payback_date:
            if isinstance(payback_date, datetime):
                return payback_date
            return datetime.combine(payback_date, time.min).replace(tzinfo=timezone.utc)
        return None

    def _get_farming_category(self, package: Optional[Package]) -> str:
        """Extract category from package."""
        if not package:
            return "General"
        cat = getattr(package, "category", None)
        if cat is not None:
            return cat.value if hasattr(cat, "value") else str(cat)
        return "General"

    async def process_investment(
        self, investor_id: uuid.UUID, data: InvestmentCreateRequest
    ) -> InvestmentResponse:
        # --- 1. Fetch & Validate Wallet ---
        wallet_stmt = select(Wallet).where(Wallet.user_id == investor_id)
        wallet_res = await self.db.execute(wallet_stmt)
        wallet = wallet_res.unique().scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet profile not found. Please setup your wallet.",
            )

        available_balance = float(wallet.available_balance or 0.0)

        if available_balance < data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient wallet balance. Available: ₦{available_balance:,.2f}, Required: ₦{data.amount:,.2f}",
            )

        # --- 2. Fetch & Validate Package ---
        package_stmt = select(Package).where(Package.id == data.package_id)
        package_res = await self.db.execute(package_stmt)
        package = package_res.unique().scalar_one_or_none()

        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investment package not found.",
            )

        pkg_status = getattr(package, "status", None)
        status_str = pkg_status.value if hasattr(pkg_status, "value") else str(pkg_status or "")
        if status_str.upper() in ["CLOSED", "COMPLETED", "INACTIVE"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This investment package is currently closed for funding.",
            )

        # --- 3. Update Wallet Balances ---
        wallet.available_balance = float(wallet.available_balance) - data.amount
        wallet.locked_funds = float(wallet.locked_funds or 0.0) + data.amount

        # --- 4. Extract Package Attributes ---
        pkg_title = getattr(package, "title", "Investment Package")
        roi_pct = self._get_package_roi(package)
        expected_returns = data.amount + (data.amount * (roi_pct / 100))
        due_date = self._get_payback_date(package)

        # --- 5. Create Investment Record ---
        new_investment = Investment(
            investor_id=investor_id,
            package_id=package.id,
            amount=data.amount,
            status=InvestmentStatus.ACTIVE,
        )

        for attr in ["payback_due_date", "due_date", "maturity_date", "repayment_date"]:
            if hasattr(new_investment, attr):
                setattr(new_investment, attr, due_date)
                break

        self.db.add(new_investment)
        await self.db.flush()

        # --- 6. Create Transaction History Record ---
        unique_ref = f"INV-{str(new_investment.id)[:8]}-{int(datetime.now(timezone.utc).timestamp())}"

        transaction = Transaction(
            wallet_id=wallet.id,
            reference=unique_ref,
            amount=data.amount,
            description=f"Investment in package: {pkg_title}",
            type=TransactionType.INVESTMENT,
            status=TransactionStatus.COMPLETED,
        )
        self.db.add(transaction)

        # --- 7. Commit Database Operations ---
        await self.db.commit()
        await self.db.refresh(new_investment)

        return InvestmentResponse(
            id=new_investment.id,
            package_id=package.id,
            package_title=pkg_title,
            farming_category=self._get_farming_category(package),
            amount=float(new_investment.amount),
            roi_percentage=roi_pct,
            expected_returns=expected_returns,
            due_date=due_date,
            status=new_investment.status.value if hasattr(new_investment.status, "value") else str(new_investment.status),
            created_at=new_investment.created_at,
        )