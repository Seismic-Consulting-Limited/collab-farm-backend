import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.cooperative_investment_model import Investment, InvestmentStatus
from app.models.package_model import Package
from app.models.user_model import User, UserRole
from app.models.wallet_model import Wallet
from app.schemas.investor_dashboard_schema import (
    FarmingCategoryAllocationItem,
    InvestorDashboardMetrics,
    InvestorDashboardResponse,
    OverdueReturnItem,
    PortfolioAllocation,
    RecentActivityItem,
    RecentInvestmentItem,
)


class InvestorDashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_due_date(self, inv: Investment):
        """Safely extract due date from Investment or Package."""
        for attr in ["due_date", "maturity_date", "repayment_date", "end_date"]:
            val = getattr(inv, attr, None)
            if val is not None:
                return val
            if inv.package:
                val = getattr(inv.package, attr, None)
                if val is not None:
                    return val
        return None

    def _get_farming_category(self, pkg: Optional[Package]) -> str:
        """Safely extract farming category/type from Package model."""
        if not pkg:
            return "General"
        for attr in ["farming_category", "category", "crop_type", "farming_type", "type"]:
            val = getattr(pkg, attr, None)
            if val is not None:
                return val.value if hasattr(val, "value") else str(val)
        return "General"

    def _extract_investor_names(self, user: User):
        """Defensively extract full_name and first_name from User or attached profiles."""
        full_name = (
            getattr(user, "company_name", None)
            or getattr(user, "full_name", None)
            or getattr(user, "name", None)
            or (
                f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip(
                )
                if getattr(user, "first_name", None)
                else None
            )
        )

        first_name = getattr(user, "first_name", None)

        profile = getattr(user, "investor_profile",
                          None) or getattr(user, "profile", None)
        if profile and not full_name:
            full_name = (
                getattr(profile, "company_name", None)
                or getattr(profile, "full_name", None)
                or getattr(profile, "name", None)
                or getattr(profile, "first_name", None)
            )
        if profile and not first_name:
            first_name = getattr(profile, "first_name", None)

        if not full_name and getattr(user, "email", None):
            full_name = user.email.split("@")[0].capitalize()

        if full_name and not first_name:
            first_name = full_name.split()[0]

        return full_name or "Investor", first_name or "Investor"

    async def get_dashboard_data(self, investor_id: uuid.UUID) -> InvestorDashboardResponse:
        # --- 0. Fetch Investor & Verify Role ---
        user_stmt = select(User).where(User.id == investor_id)
        user_res = await self.db.execute(user_stmt)
        user = user_res.unique().scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found.",
            )

        # Handle Enum or string comparison for roles safely
        user_role_str = user.role.value if hasattr(
            user.role, "value") else str(user.role)
        if user_role_str.upper() != "INVESTOR":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard metrics are only available for Investor accounts.",
            )

        investor_name, first_name = self._extract_investor_names(user)

        # --- 1. Wallet Metrics ---
        wallet_stmt = select(Wallet).where(Wallet.user_id == investor_id)
        wallet_res = await self.db.execute(wallet_stmt)
        wallet = wallet_res.unique().scalar_one_or_none()

        if wallet:
            available_balance = float(
                getattr(wallet, "available_balance", getattr(
                    wallet, "balance", getattr(wallet, "amount", 0.0))) or 0.0
            )
            locked_funds = float(
                getattr(wallet, "locked_balance", getattr(
                    wallet, "locked_funds", 0.0)) or 0.0
            )
        else:
            available_balance = 0.0
            locked_funds = 0.0

        # --- 2. Investment Metrics (Disbursed & Overdue Count) ---
        disbursed_stmt = select(func.coalesce(func.sum(Investment.amount), 0.0)).where(
            Investment.investor_id == investor_id,
            Investment.status.in_(
                [InvestmentStatus.ACTIVE, InvestmentStatus.REPAID, InvestmentStatus.OVERDUE]),
        )
        disbursed_funds = float((await self.db.execute(disbursed_stmt)).scalar() or 0.0)

        overdue_count_stmt = select(func.count(Investment.id)).where(
            Investment.investor_id == investor_id,
            Investment.status == InvestmentStatus.OVERDUE,
        )
        overdue_returns_count = (await self.db.execute(overdue_count_stmt)).scalar() or 0

        metrics = InvestorDashboardMetrics(
            available_balance=available_balance,
            locked_funds=locked_funds,
            disbursed_funds=disbursed_funds,
            overdue_returns_count=overdue_returns_count,
        )

        # --- 3. Overdue Returns List (Limit 3) ---
        overdue_stmt = (
            select(Investment)
            .options(
                selectinload(Investment.package),
                selectinload(Investment.package).selectinload(
                    Package.cooperative).selectinload(User.cooperative_profile),
            )
            .where(
                Investment.investor_id == investor_id,
                Investment.status == InvestmentStatus.OVERDUE,
            )
            .order_by(Investment.created_at.asc())
            .limit(3)
        )
        overdue_res = await self.db.execute(overdue_stmt)
        overdue_investments = overdue_res.unique().scalars().all()

        overdue_returns = [
            OverdueReturnItem(
                investment_id=inv.id,
                package_name=inv.package.title if inv.package else "Investment Package",
                cooperative_name=inv.package.cooperative.cooperative_profile.cooperative_name
                if inv.package and inv.package.cooperative and getattr(inv.package.cooperative, "cooperative_profile", None)
                else "Cooperative",
                amount=float(inv.amount),
                due_date=self._get_due_date(inv),
            )
            for inv in overdue_investments
        ]

        # --- 4. Portfolio Allocation by Farming Category ---
        active_inv_stmt = (
            select(Investment)
            .options(selectinload(Investment.package))
            .where(
                Investment.investor_id == investor_id,
                Investment.status.in_(
                    [InvestmentStatus.ACTIVE, InvestmentStatus.OVERDUE]),
            )
        )
        active_inv_res = await self.db.execute(active_inv_stmt)
        active_investments = active_inv_res.unique().scalars().all()

        category_totals = {}
        for inv in active_investments:
            cat = self._get_farming_category(inv.package)
            category_totals[cat] = category_totals.get(
                cat, 0.0) + float(inv.amount)

        total_portfolio_value = sum(category_totals.values())
        category_breakdown: List[FarmingCategoryAllocationItem] = []

        if total_portfolio_value > 0:
            for cat_name, amt_val in category_totals.items():
                percentage = round((amt_val / total_portfolio_value) * 100, 1)
                category_breakdown.append(
                    FarmingCategoryAllocationItem(
                        farming_category=cat_name,
                        amount=amt_val,
                        percentage=percentage,
                    )
                )

        portfolio_allocation = PortfolioAllocation(
            total_portfolio_value=total_portfolio_value,
            breakdown=category_breakdown,
        )

        # --- 5. Recent Investments Table & Activity Feed (Limit 5) ---
        recent_inv_stmt = (
            select(Investment)
            .options(
                selectinload(Investment.package),
                selectinload(Investment.package).selectinload(
                    Package.cooperative).selectinload(User.cooperative_profile),
            )
            .where(Investment.investor_id == investor_id)
            .order_by(Investment.created_at.desc())
            .limit(5)
        )
        recent_inv_res = await self.db.execute(recent_inv_stmt)
        recent_inv_list = recent_inv_res.unique().scalars().all()

        recent_investments = []
        recent_activities = []

        for inv in recent_inv_list:
            roi_pct = float(inv.package.roi_percentage) if inv.package and hasattr(
                inv.package, "roi_percentage") else 0.0
            expected_returns = float(inv.amount) + \
                (float(inv.amount) * (roi_pct / 100))
            pkg_title = inv.package.title if inv.package else "Investment Package"
            status_str = inv.status.value if hasattr(
                inv.status, "value") else str(inv.status)

            recent_investments.append(
                RecentInvestmentItem(
                    id=inv.id,
                    package_name=pkg_title,
                    cooperative_name=inv.package.cooperative.cooperative_profile.cooperative_name
                    if inv.package and inv.package.cooperative and getattr(inv.package.cooperative, "cooperative_profile", None)
                    else "Cooperative",
                    farming_category=self._get_farming_category(inv.package),
                    amount_invested=float(inv.amount),
                    expected_returns=expected_returns,
                    roi_percentage=roi_pct,
                    due_date=self._get_due_date(inv),
                    status=status_str,
                )
            )

            activity_title_map = {
                "PENDING": "Investment Pending Approval",
                "ACTIVE": "Fund Disbursed",
                "REPAID": "Return Received",
                "OVERDUE": "Return Overdue Alert",
            }

            recent_activities.append(
                RecentActivityItem(
                    id=inv.id,
                    title=activity_title_map.get(
                        status_str.upper(), "Investment Update"),
                    description=pkg_title,
                    timestamp=getattr(inv, "updated_at",
                                      None) or inv.created_at,
                    activity_type=status_str.lower(),
                )
            )

        return InvestorDashboardResponse(
            investor_name=investor_name,
            first_name=first_name,
            metrics=metrics,
            overdue_returns=overdue_returns,
            portfolio_allocation=portfolio_allocation,
            recent_investments=recent_investments,
            recent_activities=recent_activities,
        )
