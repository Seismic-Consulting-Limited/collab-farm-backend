import uuid
from datetime import datetime, timedelta
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.farmerModel import Farmer, WRSStatus
from app.models.packageModel import Investment, Package, PackageStatus
from app.models.profileModel import CooperativeProfile
from app.models.userModel import User, UserRole
from app.schemas.dashboard_schema import (
    CooperativeDashboardResponse,
    CropTypeBreakdown,
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

        coop_profile_res = await self.db.execute(
            select(CooperativeProfile).where(
                CooperativeProfile.user_id == user.id)
        )
        coop_profile = coop_profile_res.scalars().first()
        coop_name = coop_profile.cooperative_name if coop_profile else "Cooperative"

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        total_farmers = await self.db.scalar(
            select(func.count(Farmer.id)).where(
                Farmer.cooperative_id == user.id)
        ) or 0

        farmers_added_30d = await self.db.scalar(
            select(func.count(Farmer.id)).where(
                Farmer.cooperative_id == user.id,
                Farmer.created_at >= thirty_days_ago,
            )
        ) or 0

        verified_farmers = await self.db.scalar(
            select(func.count(Farmer.id)).where(
                Farmer.cooperative_id == user.id,
                Farmer.wrs_status == WRSStatus.VERIFIED,
            )
        ) or 0

        verified_30d = await self.db.scalar(
            select(func.count(Farmer.id)).where(
                Farmer.cooperative_id == user.id,
                Farmer.wrs_status == WRSStatus.VERIFIED,
                Farmer.created_at >= thirty_days_ago,
            )
        ) or 0

        total_acres = await self.db.scalar(
            select(func.coalesce(func.sum(Farmer.farm_size_acres), 0.0)).where(
                Farmer.cooperative_id == user.id
            )
        ) or 0.0

        acres_added_30d = await self.db.scalar(
            select(func.coalesce(func.sum(Farmer.farm_size_acres), 0.0)).where(
                Farmer.cooperative_id == user.id,
                Farmer.created_at >= thirty_days_ago,
            )
        ) or 0.0

        total_hectares = total_acres * 0.404686
        hectares_added_30d = acres_added_30d * 0.404686

        total_funding_res = await self.db.execute(
            select(func.coalesce(func.sum(Investment.amount), 0.0))
            .join(Package, Investment.package_id == Package.id)
            .where(Package.cooperative_id == user.id)
        )
        total_funding = total_funding_res.scalar() or 0.0

        crop_counts_res = await self.db.execute(
            select(Farmer.crop_type, func.count(Farmer.id))
            .where(Farmer.cooperative_id == user.id)
            .group_by(Farmer.crop_type)
        )
        crop_counts = crop_counts_res.all()

        crop_breakdown: List[CropTypeBreakdown] = []
        for crop, count in crop_counts:
            pct = round((count / total_farmers * 100),
                        1) if total_farmers > 0 else 0.0
            crop_breakdown.append(
                CropTypeBreakdown(
                    crop_type=crop or "Others", count=count, percentage=pct
                )
            )

        recent_farmers_res = await self.db.execute(
            select(Farmer)
            .where(Farmer.cooperative_id == user.id)
            .order_by(Farmer.created_at.desc())
            .limit(5)
        )
        recent_farmer_records = recent_farmers_res.scalars().all()

        recent_farmers = [
            RecentFarmerItem(
                id=f.id,
                name=f.full_name,
                crop_type=f.crop_type or "General",
                added_at=f.created_at,
                status=f.wrs_status.value if hasattr(
                    f.wrs_status, "value") else str(f.wrs_status),
            )
            for f in recent_farmer_records
        ]

        pkg_statuses = await self.db.execute(
            select(Package.status, func.count(Package.id))
            .where(Package.cooperative_id == user.id)
            .group_by(Package.status)
        )
        status_map = dict(pkg_statuses.all())

        inv_summary = InvestmentStatusSummary(
            active=status_map.get(PackageStatus.ACTIVE, 0),
            repaid=status_map.get(PackageStatus.COMPLETED, 0),
            overdue=0,
            pending=status_map.get(PackageStatus.PENDING, 0),
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
                    value=f"{total_hectares:,.0f} ha",
                    subtext=f"↑ {hectares_added_30d:,.0f} in the last 30 days.",
                ),
                total_funding_received=KpiCard(
                    value=f"₦ {total_funding / 1_000_000:.1f} Million"
                    if total_funding >= 1_000_000
                    else f"₦ {total_funding:,.2f}",
                    subtext="↑ across active packages.",
                ),
            ),
            accumulative_roi=[
                MonthlyRoiPoint(month="Dec '25", roi_percentage=70.0),
                MonthlyRoiPoint(month="Jan '26", roi_percentage=25.0),
                MonthlyRoiPoint(month="Feb '26", roi_percentage=95.0),
                MonthlyRoiPoint(month="Mar '26", roi_percentage=55.0),
                MonthlyRoiPoint(month="Apr '26", roi_percentage=80.0),
                MonthlyRoiPoint(month="May '26", roi_percentage=35.0),
            ],
            farmers_by_crop_type=crop_breakdown,
            recent_farmers=recent_farmers,
            investment_summary=inv_summary,
        )
