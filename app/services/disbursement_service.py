import math
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investment_model import Investment
from app.models.package_model import Package, PackageCategory, PackageFarmer, PackageStatus
from app.schemas.disbursement_schema import (
    DisbursementDetailResponse,
    DisbursementListItem,
    DisbursementMetrics,
    PaginatedDisbursementResponse,
)


class DisbursementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_disbursements_overview(
        self,
        cooperative_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        package_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedDisbursementResponse:
        now = datetime.now(timezone.utc)
        base_query = select(Package)

        if cooperative_id:
            base_query = base_query.where(Package.cooperative_id == cooperative_id)

        # --- 1. Compute Card Metrics ---
        total_disbursed_stmt = select(
            func.coalesce(func.sum(Package.fund_amount), 0.0)
        ).where(Package.status == PackageStatus.ACTIVE)

        pending_stmt = select(
            func.coalesce(func.sum(Package.fund_amount), 0.0),
            func.count(Package.id),
        ).where(Package.status == PackageStatus.PENDING)

        this_month_stmt = select(
            func.coalesce(func.sum(Package.fund_amount), 0.0)
        ).where(
            extract("month", Package.created_at) == now.month,
            extract("year", Package.created_at) == now.year,
        )

        total_count_stmt = select(func.count(Package.id))

        if cooperative_id:
            total_disbursed_stmt = total_disbursed_stmt.where(Package.cooperative_id == cooperative_id)
            pending_stmt = pending_stmt.where(Package.cooperative_id == cooperative_id)
            this_month_stmt = this_month_stmt.where(Package.cooperative_id == cooperative_id)
            total_count_stmt = total_count_stmt.where(Package.cooperative_id == cooperative_id)

        total_disbursed = float((await self.db.execute(total_disbursed_stmt)).scalar() or 0.0)
        pending_res = (await self.db.execute(pending_stmt)).first()
        pending_disbursement = float(pending_res[0]) if pending_res else 0.0
        pending_count = pending_res[1] if pending_res else 0
        this_month_disbursed = float((await self.db.execute(this_month_stmt)).scalar() or 0.0)
        total_disbursements_count = (await self.db.execute(total_count_stmt)).scalar() or 0

        metrics = DisbursementMetrics(
            total_disbursed=total_disbursed,
            pending_disbursement=pending_disbursement,
            pending_count=pending_count,
            this_month_disbursed=this_month_disbursed,
            total_disbursements_count=total_disbursements_count,
        )

        # --- 2. Apply Filters & Search ---
        filtered_query = base_query

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            filtered_query = filtered_query.where(
                or_(
                    Package.title.ilike(pattern),
                    Package.farming_cycle.ilike(pattern),
                )
            )

        if package_type and package_type.lower() != "all":
            category_key = package_type.strip().upper().replace(" ", "_")
            if category_key in PackageCategory.__members__:
                filtered_query = filtered_query.where(
                    Package.category == PackageCategory[category_key]
                )

        if status_filter and status_filter.upper() in PackageStatus.__members__:
            filtered_query = filtered_query.where(
                Package.status == PackageStatus[status_filter.upper()]
            )

        count_stmt = select(func.count()).select_from(filtered_query.subquery())
        total_filtered = (await self.db.execute(count_stmt)).scalar() or 0

        # --- 3. Pagination & Count Mapping ---
        offset = (page - 1) * page_size
        paginated_query = (
            filtered_query.order_by(Package.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(paginated_query)
        packages = result.scalars().all()

        items = []
        for pkg in packages:
            investors_count = (
                await self.db.execute(
                    select(func.count(Investment.id)).where(Investment.package_id == pkg.id)
                )
            ).scalar() or 0

            farmers_count = (
                await self.db.execute(
                    select(func.count(PackageFarmer.id)).where(PackageFarmer.package_id == pkg.id)
                )
            ).scalar() or 0

            items.append(
                DisbursementListItem(
                    id=pkg.id,
                    package_name=pkg.title,
                    category=pkg.category,
                    investors_count=investors_count,
                    farmers_count=farmers_count,
                    amount=float(pkg.fund_amount),
                    date_invested=pkg.created_at,
                    status=pkg.status,
                )
            )

        total_pages = math.ceil(total_filtered / page_size) if page_size > 0 else 1

        return PaginatedDisbursementResponse(
            metrics=metrics,
            items=items,
            total=total_filtered,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_disbursement_detail(self, package_id: uuid.UUID) -> DisbursementDetailResponse:
        pkg = await self.db.get(Package, package_id)
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package with ID '{package_id}' not found.",
            )

        investors_count = (
            await self.db.execute(
                select(func.count(Investment.id)).where(Investment.package_id == pkg.id)
            )
        ).scalar() or 0

        farmers_count = (
            await self.db.execute(
                select(func.count(PackageFarmer.id)).where(PackageFarmer.package_id == pkg.id)
            )
        ).scalar() or 0

        total_amount = float(pkg.fund_amount)
        is_active = pkg.status == PackageStatus.ACTIVE

        return DisbursementDetailResponse(
            id=pkg.id,
            package_name=pkg.title,
            package_code=f"PKG-{str(pkg.id)[:8].upper()}",
            category=pkg.category,
            crop_type=pkg.farming_cycle,
            total_package_amount=total_amount,
            currently_disbursed=total_amount if is_active else 0.0,
            remaining_to_disburse=0.0 if is_active else total_amount,
            investors_count=investors_count,
            farmers_count=farmers_count,
            status=pkg.status,
        )