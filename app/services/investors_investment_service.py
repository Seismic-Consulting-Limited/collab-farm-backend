import uuid
from datetime import datetime, time, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cooperative_investment_model import Investment, InvestmentStatus
from app.models.package_model import Package
from app.models.wallet_model import (
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
)
from app.schemas.investors_investment_schema import (
    InvestmentCreateRequest,
    InvestmentResponse,
    PackageFundingProgress,
    InvestmentSummaryMetrics,
    InvestorInvestmentDetailResponse,
    InvestorInvestmentListItem,
    InvestorInvestmentsOverviewResponse,
    YourInvestmentDetails,
    SettlementInformation,
)


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
        status_str = pkg_status.value if hasattr(
            pkg_status, "value") else str(pkg_status or "")
        if status_str.upper() in ["CLOSED", "COMPLETED", "INACTIVE"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This investment package is currently closed for funding.",
            )

        # --- 3. Check for Active or Pending Investment in THIS Package ---
        active_statuses = [InvestmentStatus.ACTIVE, InvestmentStatus.PENDING]
        existing_inv_stmt = select(Investment).where(
            Investment.investor_id == investor_id,
            Investment.package_id == data.package_id,
            Investment.status.in_(active_statuses),
        )
        existing_inv_res = await self.db.execute(existing_inv_stmt)
        existing_investment = existing_inv_res.scalars().first()

        if existing_investment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "You already have an ongoing investment in this package. "
                    "You cannot reinvest in the same package until your current investment is completed."
                ),
            )

        # --- 4. Update Wallet Balances ---
        wallet.available_balance = float(
            wallet.available_balance) - data.amount
        wallet.locked_funds = float(wallet.locked_funds or 0.0) + data.amount

        # --- 5. Extract Package Attributes ---
        pkg_title = getattr(package, "title", "Investment Package")
        roi_pct = self._get_package_roi(package)
        expected_returns = data.amount + (data.amount * (roi_pct / 100))
        due_date = self._get_payback_date(package)

        # --- 6. Create Investment Record ---
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

        # --- 7. Create Transaction History Record ---
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

        # --- 8. Commit Database Operations ---
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
            status=new_investment.status.value if hasattr(
                new_investment.status, "value") else str(new_investment.status),
            created_at=new_investment.created_at,
        )

    async def get_investor_investments(
        self,
        investor_id: uuid.UUID,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> InvestorInvestmentsOverviewResponse:
        # Fetch all investments for this investor with loaded package relationships
        stmt = (
            select(Investment)
            .options(selectinload(Investment.package))
            .where(Investment.investor_id == investor_id)
            .order_by(Investment.created_at.desc())
        )
        res = await self.db.execute(stmt)
        all_investments = res.scalars().all()

        # Calculate Summary Metrics
        total_invested = sum(float(inv.amount) for inv in all_investments)

        active_investments = sum(
            float(inv.amount)
            for inv in all_investments
            if str(getattr(inv.status, "value", inv.status)).upper() == "ACTIVE"
        )

        packages_funded = sum(
            float(inv.amount)
            for inv in all_investments
            if str(getattr(inv.status, "value", inv.status)).upper() in ["ACTIVE", "COMPLETED"]
        )

        pending_settlement = 0.0
        items: List[InvestorInvestmentListItem] = []

        for inv in all_investments:
            pkg = inv.package
            pkg_title = getattr(
                pkg, "title", "Investment Package") if pkg else "Investment Package"
            pkg_type = getattr(pkg, "package_type",
                               "Standard") if pkg else "Standard"
            pkg_type_str = pkg_type.value if hasattr(
                pkg_type, "value") else str(pkg_type)

            roi_pct = self._get_package_roi(pkg) if pkg else 0.0
            expected_settlement = float(
                inv.amount) + (float(inv.amount) * (roi_pct / 100))

            inv_status = inv.status.value if hasattr(
                inv.status, "value") else str(inv.status)
            if inv_status.upper() in ["ACTIVE", "PENDING"]:
                pending_settlement += expected_settlement

            # Package funding progress %
            fund_amount = float(
                getattr(pkg, "fund_amount", 1.0) or 1.0) if pkg else 1.0
            amount_raised = float(
                getattr(pkg, "amount_raised", 0.0) or 0.0) if pkg else 0.0
            progress_pct = min(
                round((amount_raised / fund_amount) * 100, 1), 100.0)

            # Apply Search & Filter if requested
            if status_filter and status_filter.upper() != "ALL":
                if inv_status.upper() != status_filter.upper():
                    continue

            if search:
                if search.lower() not in pkg_title.lower():
                    continue

            items.append(
                InvestorInvestmentListItem(
                    id=inv.id,
                    package_id=inv.package_id,
                    package_title=pkg_title,
                    category=self._get_farming_category(pkg),
                    package_type=pkg_type_str,
                    amount_invested=float(inv.amount),
                    funding_progress_percentage=progress_pct,
                    expected_settlement=expected_settlement,
                    date_invested=inv.created_at,
                    status=inv_status.capitalize(),
                )
            )

        summary = InvestmentSummaryMetrics(
            total_invested=total_invested,
            active_investments=active_investments,
            packages_funded=packages_funded,
            pending_settlement=pending_settlement,
        )

        return InvestorInvestmentsOverviewResponse(
            summary=summary,
            investments=items,
            total_count=len(items),
        )

    async def get_investor_investment_detail(
        self, investor_id: uuid.UUID, investment_id: uuid.UUID
    ) -> InvestorInvestmentDetailResponse:
        stmt = (
            select(Investment)
            .options(selectinload(Investment.package))
            .where(
                Investment.id == investment_id,
                Investment.investor_id == investor_id,
            )
        )
        res = await self.db.execute(stmt)
        investment = res.unique().scalar_one_or_none()

        if not investment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investment record not found.",
            )

        pkg = investment.package
        pkg_title = getattr(
            pkg, "title", "Investment Package") if pkg else "Investment Package"

        # Transaction reference lookup
        tx_stmt = select(Transaction).where(
            Transaction.description.ilike(f"%{pkg_title}%")
        ).order_by(Transaction.created_at.desc())
        tx_res = await self.db.execute(tx_stmt)
        tx = tx_res.scalars().first()
        tx_ref = tx.reference if tx else f"TX-{str(investment.id)[:8].upper()}"

        # Package Metrics
        target_amount = float(
            getattr(pkg, "fund_amount", 0.0) or 0.0) if pkg else 0.0
        amount_raised = float(
            getattr(pkg, "amount_raised", 0.0) or 0.0) if pkg else 0.0
        progress_pct = min(round((amount_raised / target_amount)
                           * 100, 1), 100.0) if target_amount > 0 else 0.0

        assigned_farmers = getattr(pkg, "assigned_farmers", []) if pkg else []
        farmers_count = len(assigned_farmers) if isinstance(
            assigned_farmers, list) else 0

        roi_pct = self._get_package_roi(pkg) if pkg else 0.0
        expected_settlement = float(
            investment.amount) + (float(investment.amount) * (roi_pct / 100))
        due_date = self._get_payback_date(pkg) if pkg else None

        inv_status_str = (
            investment.status.value
            if hasattr(investment.status, "value")
            else str(investment.status)
        )

        return InvestorInvestmentDetailResponse(
            investment_id=investment.id,
            package_id=investment.package_id,
            package_title=pkg_title,
            package_code=f"INV-{str(investment.id)[:4].upper()}",
            category=self._get_farming_category(pkg),
            invested_date_str=investment.created_at.strftime(
                "%d %b %Y, %I:%M %p"),
            investment_details=YourInvestmentDetails(
                amount_invested=float(investment.amount),
                investment_id_code=f"#{float(investment.amount):,.0f}",
                date_invested=investment.created_at,
                transaction_reference=tx_ref,
                status=inv_status_str.capitalize(),
            ),
            package_progress=PackageFundingProgress(
                progress_percentage=progress_pct,
                amount_raised=amount_raised,
                target_amount=target_amount,
                farmers_supported=farmers_count,
                total_farm_size_ha=getattr(pkg, "total_farm_size", 18.5),
                locations_count=getattr(pkg, "locations_count", 3),
            ),
            settlement_info=SettlementInformation(
                expected_settlement_date=due_date,
                expected_settlement_amount=expected_settlement,
            ),
        )
