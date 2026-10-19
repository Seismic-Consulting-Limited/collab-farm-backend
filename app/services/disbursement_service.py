import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.disbursement_model import Disbursement, DisbursementStatus
from app.models.package_model import Package, PackageCategory
from app.models.user_model import User, UserRole
from app.schemas.disbursement_schema import (
    DisbursementDetailResponse,
    DisbursementFarmerSummary,
    DisbursementListItem,
    DisbursementMetrics,
    DisbursementPackageSummary,
    PaginatedDisbursementResponse,
)


class DisbursementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_disbursements_overview(
        self,
        user: User,
        search: Optional[str] = None,
        package_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedDisbursementResponse:
        # 1. Enforce Cooperative Role Check
        if user.role != UserRole.COOPERATIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Cooperatives can view disbursement metrics.",
            )

        cooperative_id = user.id
        now = datetime.now(timezone.utc)

        # --- Compute Summary KPI Card Metrics ---
        total_disbursed_stmt = (
            select(func.coalesce(func.sum(Disbursement.amount), 0.0))
            .where(
                Disbursement.cooperative_id == cooperative_id,
                Disbursement.status.in_(
                    [DisbursementStatus.DISBURSED, DisbursementStatus.COMPLETED]),
            )
        )

        pending_stmt = (
            select(
                func.coalesce(func.sum(Disbursement.amount), 0.0),
                func.count(Disbursement.id),
            )
            .where(
                Disbursement.cooperative_id == cooperative_id,
                Disbursement.status.in_(
                    [DisbursementStatus.PENDING, DisbursementStatus.REVIEWING]),
            )
        )

        this_month_stmt = (
            select(func.coalesce(func.sum(Disbursement.amount), 0.0))
            .where(
                Disbursement.cooperative_id == cooperative_id,
                Disbursement.status.in_(
                    [DisbursementStatus.DISBURSED, DisbursementStatus.COMPLETED]),
                extract("month", Disbursement.disbursement_date) == now.month,
                extract("year", Disbursement.disbursement_date) == now.year,
            )
        )

        total_count_stmt = (
            select(func.count(Disbursement.id))
            .where(Disbursement.cooperative_id == cooperative_id)
        )

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

        # --- Build Base List Query with Eager Loading ---
        base_query = (
            select(Disbursement)
            .join(Disbursement.farmer)
            .join(Disbursement.package)
            .options(
                selectinload(Disbursement.farmer),
                selectinload(Disbursement.package),
            )
            .where(Disbursement.cooperative_id == cooperative_id)
        )

        # --- Apply Search ---
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            base_query = base_query.where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                    Package.title.ilike(pattern),
                    Disbursement.transaction_reference.ilike(pattern),
                )
            )

        # --- Apply Package Category / Type Filter ---
        if package_type and package_type.lower() != "all":
            category_key = package_type.strip().upper().replace(" ", "_")
            if category_key in PackageCategory.__members__:
                base_query = base_query.where(
                    Package.category == PackageCategory[category_key]
                )

        # --- Apply Disbursement Status Filter ---
        if status_filter and status_filter.upper() in DisbursementStatus.__members__:
            base_query = base_query.where(
                Disbursement.status == DisbursementStatus[status_filter.upper(
                )]
            )

        # Total Filtered Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_filtered = (await self.db.execute(count_stmt)).scalar() or 0

        # --- Pagination Execution ---
        offset = (page - 1) * page_size
        paginated_query = (
            base_query.order_by(Disbursement.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(paginated_query)
        disbursements = result.scalars().all()

        items = []
        for disb in disbursements:
            farmer_user = disb.farmer
            farmer_name = (
                f"{getattr(farmer_user, 'first_name', '') or ''} {getattr(farmer_user, 'last_name', '') or ''}".strip()
                or getattr(farmer_user, "email", "")
            )

            farmer_summary = DisbursementFarmerSummary(
                id=farmer_user.id,
                full_name=farmer_name,
                farmer_code=getattr(farmer_user, "farmer_code",
                                    f"PKG-{str(farmer_user.id)[:5].upper()}"),
                photo_url=getattr(farmer_user, "photo_url", None),
            )

            package_summary = DisbursementPackageSummary(
                id=disb.package.id,
                title=disb.package.title,
                category=disb.package.category,
                package_type=getattr(disb.package, "package_type", None),
            )

            items.append(
                DisbursementListItem(
                    id=disb.id,
                    farmer=farmer_summary,
                    package=package_summary,
                    amount_disbursed=float(disb.amount),
                    disbursement_date=disb.disbursement_date,
                    status=disb.status,
                )
            )

        total_pages = math.ceil(
            total_filtered / page_size) if page_size > 0 else 1

        return PaginatedDisbursementResponse(
            metrics=metrics,
            items=items,
            total=total_filtered,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_disbursement_detail(
        self, user: User, disbursement_id: uuid.UUID
    ) -> DisbursementDetailResponse:
        # 1. Enforce Cooperative Role Check
        if user.role != UserRole.COOPERATIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Cooperatives can view disbursement details.",
            )

        query = (
            select(Disbursement)
            .options(
                selectinload(Disbursement.farmer),
                selectinload(Disbursement.package),
                selectinload(Disbursement.recorded_by),
            )
            .where(Disbursement.id == disbursement_id)
        )
        result = await self.db.execute(query)
        disb = result.scalars().first()

        if not disb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Disbursement record with ID '{disbursement_id}' not found.",
            )

        # 2. Enforce Cooperative Ownership Check
        if disb.cooperative_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized. You do not own this disbursement record.",
            )

        farmer_user = disb.farmer
        farmer_name = (
            f"{getattr(farmer_user, 'first_name', '') or ''} {getattr(farmer_user, 'last_name', '') or ''}".strip()
            or getattr(farmer_user, "email", "")
        )

        farmer_code = getattr(
            farmer_user, "farmer_code", f"PKG-{str(disb.id)[:5].upper()}"
        )

        recorded_by_name = "Admin User"
        if disb.recorded_by:
            recorded_by_name = (
                f"{getattr(disb.recorded_by, 'first_name', '') or ''} {getattr(disb.recorded_by, 'last_name', '') or ''}".strip()
                or disb.recorded_by.email
            )

        return DisbursementDetailResponse(
            id=disb.id,
            farmer_id_code=farmer_code,
            farmer_name=farmer_name,
            photo_url=getattr(farmer_user, "photo_url", None),
            status=disb.status,
            amount_disbursed=float(disb.amount),
            disbursed_at=disb.disbursement_date,
            recorded_by=recorded_by_name,
            transaction_reference=disb.transaction_reference,
            package_title=disb.package.title if disb.package else None,
        )
