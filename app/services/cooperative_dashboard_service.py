import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.farmer_model import Farmer, Farm, WRSStatus
from app.models.package_model import Package, PackageFarmer
from app.models.profile_model import CooperativeProfile
from app.models.user_model import User, UserRole
from app.models.cooperative_investment_model import Investment, InvestmentStatus
from app.models.settlement_model import Settlement, SettlementStatus
from app.schemas.cooperative_dashboard_schema import (
    CooperativeDashboardResponse,
    FarmingCategoryBreakdown,
    DashboardKpis,
    InvestmentStatusSummary,
    KpiCard,
    MonthlyRoiPoint,
    RecentFarmerItem,
)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cooperative_dashboard(self, user: User) -> CooperativeDashboardResponse:
        if user.role != UserRole.COOPERATIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard metrics are only available for Cooperative accounts.",
            )

        # Fetch Cooperative Profile Name
        coop_profile_res = await self.db.execute(
            select(CooperativeProfile).where(
                CooperativeProfile.user_id == user.id
            )
        )
        coop_profile = coop_profile_res.scalars().first()
        coop_name = coop_profile.cooperative_name if coop_profile else "Cooperative"

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # Subquery to capture all farmer IDs associated with this cooperative directly or via packages
        coop_farmer_ids_stmt = select(Farmer.id).where(
            or_(
                Farmer.cooperative_id == user.id,
                Farmer.id.in_(
                    select(PackageFarmer.farmer_id)
                    .join(Package, PackageFarmer.package_id == Package.id)
                    .where(Package.cooperative_id == user.id)
                ),
            )
        )

        # 1. Total Farmers
        total_farmers = await self.db.scalar(
            select(func.count(func.distinct(Farmer.id))).where(Farmer.id.in_(coop_farmer_ids_stmt))
        ) or 0

        farmers_added_30d = await self.db.scalar(
            select(func.count(func.distinct(Farmer.id))).where(
                Farmer.id.in_(coop_farmer_ids_stmt),
                Farmer.created_at >= thirty_days_ago,
            )
        ) or 0

        # 2. Verified Farmers
        verified_farmers = await self.db.scalar(
            select(func.count(func.distinct(Farmer.id))).where(
                Farmer.id.in_(coop_farmer_ids_stmt),
                Farmer.wrs_status == WRSStatus.VERIFIED,
            )
        ) or 0

        verified_30d = await self.db.scalar(
            select(func.count(func.distinct(Farmer.id))).where(
                Farmer.id.in_(coop_farmer_ids_stmt),
                Farmer.wrs_status == WRSStatus.VERIFIED,
                Farmer.created_at >= thirty_days_ago,
            )
        ) or 0

        # 3. Farm Hectares Queries (Aggregated from Farm.size_in_hectares)
        total_hectares_stmt = (
            select(func.coalesce(func.sum(Farm.size_in_hectares), 0.0))
            .select_from(Farm)
            .where(Farm.farmer_id.in_(coop_farmer_ids_stmt))
        )
        total_hectares_res = await self.db.execute(total_hectares_stmt)
        total_hectares = float(total_hectares_res.scalar() or 0.0)

        hectares_30d_stmt = (
            select(func.coalesce(func.sum(Farm.size_in_hectares), 0.0))
            .select_from(Farm)
            .where(
                Farm.farmer_id.in_(coop_farmer_ids_stmt),
                Farm.created_at >= thirty_days_ago,
            )
        )
        hectares_30d_res = await self.db.execute(hectares_30d_stmt)
        hectares_added_30d = float(hectares_30d_res.scalar() or 0.0)

        # 4. Total Funding
        total_funding_res = await self.db.execute(
            select(func.coalesce(func.sum(Investment.amount), 0.0))
            .join(Package, Investment.package_id == Package.id)
            .where(Package.cooperative_id == user.id)
        )
        total_funding = float(total_funding_res.scalar() or 0.0)

        # 5. Farming Category Breakdowns
        cat_counts_res = await self.db.execute(
            select(
                func.coalesce(Farm.farming_category, Farmer.farming_category),
                func.count(func.distinct(Farmer.id)),
            )
            .outerjoin(Farm, Farmer.id == Farm.farmer_id)
            .where(Farmer.id.in_(coop_farmer_ids_stmt))
            .group_by(func.coalesce(Farm.farming_category, Farmer.farming_category))
        )
        cat_counts = cat_counts_res.all()

        farming_category_breakdown: List[FarmingCategoryBreakdown] = []
        for cat, count in cat_counts:
            pct = round((count / total_farmers * 100), 1) if total_farmers > 0 else 0.0
            raw_cat = cat.value if hasattr(cat, "value") else str(cat or "General")
            formatted_cat = raw_cat.replace("_", " ").title() if raw_cat else "General"

            farming_category_breakdown.append(
                FarmingCategoryBreakdown(
                    farming_category=formatted_cat,
                    count=count,
                    percentage=pct,
                )
            )

        # 6. Recent Farmers
        recent_farmers_res = await self.db.execute(
            select(Farmer)
            .where(Farmer.id.in_(coop_farmer_ids_stmt))
            .order_by(Farmer.created_at.desc())
            .limit(5)
        )
        recent_farmer_records = recent_farmers_res.scalars().all()

        recent_farmers = []
        for f in recent_farmer_records:
            category_val = "General"
            if f.farming_category:
                raw_cat = f.farming_category.value if hasattr(f.farming_category, "value") else str(f.farming_category)
                category_val = raw_cat.replace("_", " ").title()
            else:
                first_farm_res = await self.db.execute(
                    select(Farm.farming_category).where(Farm.farmer_id == f.id).limit(1)
                )
                farm_cat = first_farm_res.scalar()
                if farm_cat:
                    raw_cat = farm_cat.value if hasattr(farm_cat, "value") else str(farm_cat)
                    category_val = raw_cat.replace("_", " ").title()

            recent_farmers.append(
                RecentFarmerItem(
                    id=f.id,
                    name=f.full_name,
                    farming_category=category_val,
                    added_at=f.created_at,
                    status=f.wrs_status.value if hasattr(f.wrs_status, "value") else str(f.wrs_status),
                )
            )

        # 7. Investment Summary
        investment_statuses = await self.db.execute(
            select(Investment.status, func.count(Investment.id))
            .join(Package, Investment.package_id == Package.id)
            .where(Package.cooperative_id == user.id)
            .group_by(Investment.status)
        )
        investment_status_map = dict(investment_statuses.all())

        inv_summary = InvestmentStatusSummary(
            active=investment_status_map.get(InvestmentStatus.ACTIVE, 0),
            repaid=investment_status_map.get(InvestmentStatus.REPAID, 0),
            overdue=investment_status_map.get(InvestmentStatus.OVERDUE, 0),
            pending=investment_status_map.get(InvestmentStatus.PENDING, 0),
        )

        # 8. Cumulative ROI from packages with at least one settled settlement.
        settled_package_res = await self.db.execute(
            select(
                Package.id,
                Package.cooperative_share,
                func.min(Settlement.date_settled),
            )
            .join(Settlement, Settlement.package_id == Package.id)
            .where(
                Package.cooperative_id == user.id,
                Settlement.status == SettlementStatus.SETTLED,
                Settlement.date_settled.is_not(None),
            )
            .group_by(Package.id, Package.cooperative_share)
        )
        roi_by_month = {}
        for _package_id, cooperative_share, settled_at in settled_package_res.all():
            month_key = (settled_at.year, settled_at.month)
            roi_by_month[month_key] = roi_by_month.get(month_key, 0.0) + float(cooperative_share or 0.0)

        now = datetime.now(timezone.utc)
        current_month_index = now.year * 12 + now.month - 1
        chart_months = []
        for offset in range(5, -1, -1):
            month_index = current_month_index - offset
            year, zero_based_month = divmod(month_index, 12)
            month = zero_based_month + 1
            chart_months.append((year, month))

        cumulative_roi = sum(
            roi for (year, month), roi in roi_by_month.items()
            if (year, month) < chart_months[0]
        )
        accumulative_roi = []
        for year, month in chart_months:
            cumulative_roi += roi_by_month.get((year, month), 0.0)
            accumulative_roi.append(
                MonthlyRoiPoint(
                    month=datetime(year, month, 1).strftime("%b '%y"),
                    roi_percentage=round(cumulative_roi, 2),
                )
            )

        return CooperativeDashboardResponse(
            greeting_name=user.first_name or "Partner",
            cooperative_name=coop_name,
            kpis=DashboardKpis(
                total_farmers=KpiCard(
                    value=str(total_farmers),
                    badge_value=f"+{farmers_added_30d}",
                    subtext=f"↑ {farmers_added_30d} in the last 30 days.",
                ),
                verified_farmers=KpiCard(
                    value=str(verified_farmers),
                    badge_value=f"+{verified_30d}",
                    subtext=f"↑ {verified_30d} in the last 30 days.",
                ),
                total_farm_area=KpiCard(
                    value=f"{total_hectares:,.1f} ha",
                    subtext=f"↑ {hectares_added_30d:,.1f} in the last 30 days.",
                ),
                total_funding_received=KpiCard(
                    value=f"₦ {total_funding / 1_000_000:.1f} Million"
                    if total_funding >= 1_000_000
                    else f"₦ {total_funding:,.2f}",
                    subtext="↑ across active packages.",
                ),
            ),
            accumulative_roi=accumulative_roi,
            farmers_by_farming_category=farming_category_breakdown,
            recent_farmers=recent_farmers,
            investment_summary=inv_summary,
        )
