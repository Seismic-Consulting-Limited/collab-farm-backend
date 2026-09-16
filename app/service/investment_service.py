import math
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.packageModel import Investment, Package, PackageStatus
from app.models.userModel import InvestorType
from app.models.userModel import User, UserRole
from app.schemas.investment_schema import (
    InvestmentKpis,
    InvestmentListItem,
    KpiMetricCard,
    PaginatedInvestmentsResponse,
)


class InvestmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _calculate_metric_with_30d_growth(
        self, base_select, cooperative_id: uuid.UUID, extra_filter=None
    ) -> Tuple[float, float, bool]:
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        query = base_select.join(Package, Investment.package_id == Package.id).where(
            Package.cooperative_id == cooperative_id
        )

        if extra_filter is not None:
            query = query.where(extra_filter)

        total_val = (await self.db.execute(query)).scalar() or 0.0

        curr_30d_res = await self.db.execute(
            query.where(Investment.created_at >= thirty_days_ago)
        )
        curr_30d_val = curr_30d_res.scalar() or 0.0

        prev_30d_res = await self.db.execute(
            query.where(
                Investment.created_at >= sixty_days_ago,
                Investment.created_at < thirty_days_ago,
            )
        )
        prev_30d_val = prev_30d_res.scalar() or 0.0

        if prev_30d_val == 0.0:
            growth_pct = 100.0 if curr_30d_val > 0 else 0.0
        else:
            growth_pct = round(
                ((curr_30d_val - prev_30d_val) / prev_30d_val) * 100, 1)

        is_positive = growth_pct >= 0
        return total_val, abs(growth_pct), is_positive

    async def get_cooperative_investments(
        self, user: User, page: int = 1, limit: int = 10
    ) -> PaginatedInvestmentsResponse:
        if user.role != UserRole.COOPERATIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Investment records are only accessible to Cooperative accounts.",
            )

        now = datetime.utcnow()

        total_inv, total_growth, total_pos = await self._calculate_metric_with_30d_growth(
            select(func.coalesce(func.sum(Investment.amount), 0.0)),
            user.id,
        )

        active_inv, active_growth, active_pos = await self._calculate_metric_with_30d_growth(
            select(func.coalesce(func.sum(Investment.amount), 0.0)),
            user.id,
            extra_filter=(Package.status == PackageStatus.ACTIVE),
        )

        expected_inv, exp_growth, exp_pos = await self._calculate_metric_with_30d_growth(
            select(func.coalesce(func.sum(Investment.amount), 0.0)),
            user.id,
            extra_filter=(
                Package.status.in_(
                    [PackageStatus.ACTIVE, PackageStatus.PENDING])
            ),
        )

        total_count_res = await self.db.execute(
            select(func.count(Investment.id))
            .join(Package, Investment.package_id == Package.id)
            .where(Package.cooperative_id == user.id)
        )
        total_count = total_count_res.scalar() or 0

        overdue_count_res = await self.db.execute(
            select(func.count(Investment.id))
            .join(Package, Investment.package_id == Package.id)
            .where(
                Package.cooperative_id == user.id,
                Package.status == PackageStatus.ACTIVE,
                Package.start_date +
                timedelta(days=30 * Package.duration_months) < now
                if hasattr(Package, "duration_months")
                else Package.status == PackageStatus.ACTIVE,
            )
        )
        overdue_count = overdue_count_res.scalar() or 0

        overdue_rate = (
            round((overdue_count / total_count) *
                  100, 1) if total_count > 0 else 0.0
        )

        kpis = InvestmentKpis(
            total_invested=KpiMetricCard(
                value=f"₦ {total_inv:,.2f}",
                change_percentage=f"{total_growth}%",
                is_positive=total_pos,
                subtext="in the last 30 days.",
            ),
            active_investments=KpiMetricCard(
                value=f"₦ {active_inv:,.2f}",
                change_percentage=f"{active_growth}%",
                is_positive=active_pos,
                subtext="in the last 30 days.",
            ),
            expected_settlement=KpiMetricCard(
                value=f"₦ {expected_inv:,.2f}",
                change_percentage=f"{exp_growth}%",
                is_positive=exp_pos,
                subtext="in the last 30 days.",
            ),
            overdue_rate=KpiMetricCard(
                value=f"{overdue_rate}%",
                change_percentage="0.0%",
                is_positive=True,
                subtext="in the last 30 days.",
            ),
        )

        offset = (page - 1) * limit
        query = (
            select(Investment)
            .join(Package, Investment.package_id == Package.id)
            .options(
                selectinload(Investment.package),
                selectinload(Investment.investor),
            )
            .where(Package.cooperative_id == user.id)
            .order_by(Investment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        investments = result.scalars().all()

        items: List[InvestmentListItem] = []
        for inv in investments:
            investor_user = inv.investor
            investor_name = (
                f"{investor_user.first_name} {investor_user.last_name}".strip()
                if investor_user and (investor_user.first_name or investor_user.last_name)
                else (investor_user.email if investor_user else "N/A")
            )

            profile_res = await self.db.execute(
                select(InvestorType).where(
                    InvestorType.user_id == inv.investor_id)
            )
            profile = profile_res.scalars().first()
            location = profile.state if profile and profile.state else "Unspecified"

            inv_code = f"LN-{inv.created_at.strftime('%y')}-{str(inv.id)[:6].upper()}"

            pkg_status = inv.package.status if inv.package else "UNKNOWN"
            status_str = (
                pkg_status.value if hasattr(
                    pkg_status, "value") else str(pkg_status)
            )

            items.append(
                InvestmentListItem(
                    id=inv.id,
                    investor_name=investor_name,
                    investor_location=location,
                    investor_code=inv_code,
                    package_title=inv.package.title if inv.package else "N/A",
                    amount=inv.amount,
                    date_invested=inv.created_at,
                    status=status_str,
                )
            )

        pages = math.ceil(total_count / limit) if limit > 0 else 1

        return PaginatedInvestmentsResponse(
            kpis=kpis,
            items=items,
            total=total_count,
            page=page,
            limit=limit,
            pages=pages,
        )
