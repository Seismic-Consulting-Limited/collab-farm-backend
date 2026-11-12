import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.disbursement_model import Disbursement, DisbursementStatus
from app.models.settlement_model import Settlement, SettlementStatus
from app.models.farmer_model import Farmer
from app.models.package_model import Package
from app.models.cooperative_investment_model import Investment
from app.models.user_model import User
from app.schemas.disbursement_schema import (
    DisbursementMetricsResponse,
    DisbursementDetailResponse,
    DisbursementListItemResponse,
    DisbursementTrancheSchema,
    FarmerSummarySchema,
    PackageSummarySchema,
    DisbursementStatusUpdateSchema,
)
from app.utils.funding_plan import calculate_funding_progress
from app.services.notification_service import add_notification


def _get_user_display_name(user: Optional[User]) -> str:
    if not user:
        return "System Automated"

    first = getattr(user, "first_name", "") or ""
    last = getattr(user, "last_name", "") or ""
    full_name = f"{first} {last}".strip()

    return full_name if full_name else getattr(user, "email", "Admin User")


class DisbursementService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _package_funding_progress(package: Package) -> dict:
        released_statuses = {
            DisbursementStatus.DISBURSED,
            DisbursementStatus.COMPLETED,
        }
        released_disbursements = [
            disbursement
            for disbursement in package.disbursements
            if disbursement.status in released_statuses
        ]
        total_released = sum(
            float(disbursement.amount or 0) for disbursement in released_disbursements
        )
        return calculate_funding_progress(
            float(package.fund_amount or 0),
            total_released,
            [
                {
                    "amount": disbursement.amount,
                    "released_at": disbursement.disbursement_date,
                }
                for disbursement in released_disbursements
            ],
            category=package.category,
        )

    @staticmethod
    def _current_tranche_disbursed_amount(progress: dict) -> float:
        current_tranche = next(
            (tranche for tranche in progress["tranches"] if tranche["is_current"]),
            None,
        )
        return float(current_tranche["released_amount"]) if current_tranche else 0.0

    @staticmethod
    def _most_recent_disbursement_date(package: Package, fallback: datetime) -> datetime:
        released_statuses = {
            DisbursementStatus.DISBURSED,
            DisbursementStatus.COMPLETED,
        }
        dates = [
            disbursement.disbursement_date
            for disbursement in package.disbursements
            if disbursement.status in released_statuses
            and disbursement.disbursement_date is not None
        ]
        return max(dates) if dates else fallback

    @staticmethod
    async def create_auto_disbursement_on_assignment(
        session: AsyncSession,
        farmer_id: uuid.UUID,
        package_id: uuid.UUID,
        cooperative_id: uuid.UUID,
        amount: float,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> Disbursement:
        reference = f"DSB-{uuid.uuid4().hex[:10].upper()}"

        disbursement = Disbursement(
            farmer_id=farmer_id,
            package_id=package_id,
            cooperative_id=cooperative_id,
            recorded_by_id=admin_user_id,
            amount=amount,
            transaction_reference=reference,
            status=DisbursementStatus.PENDING,
        )
        session.add(disbursement)
        await session.commit()
        await session.refresh(disbursement)
        return disbursement

    async def get_metrics(self, cooperative_id: uuid.UUID) -> DisbursementMetricsResponse:
        now = datetime.now(timezone.utc)
        first_day_this_month = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)

        # 1. Total Disbursed
        total_query = select(
            func.coalesce(func.sum(Disbursement.amount), 0.0)
        ).where(
            Disbursement.cooperative_id == cooperative_id,
            Disbursement.status == DisbursementStatus.DISBURSED,
        )
        total_disbursed = (await self.session.execute(total_query)).scalar_one()

        # 2. Pending Disbursements
        pending_query = select(
            func.coalesce(func.sum(Disbursement.amount), 0.0),
            func.count(Disbursement.id),
        ).where(
            Disbursement.cooperative_id == cooperative_id,
            Disbursement.status == DisbursementStatus.PENDING,
        )
        pending_res = (await self.session.execute(pending_query)).one()
        pending_amount, pending_count = pending_res[0], pending_res[1]

        # 3. This Month Total
        this_month_query = select(
            func.coalesce(func.sum(Disbursement.amount), 0.0)
        ).where(
            Disbursement.cooperative_id == cooperative_id,
            Disbursement.created_at >= first_day_this_month,
            Disbursement.status == DisbursementStatus.DISBURSED,
        )
        this_month_amount = (await self.session.execute(this_month_query)).scalar_one()

        # 4. Total Disbursements Count
        total_count_query = select(func.count(Disbursement.id)).where(
            Disbursement.cooperative_id == cooperative_id
        )
        total_count = (await self.session.execute(total_count_query)).scalar_one()

        return DisbursementMetricsResponse(
            total_disbursed=float(total_disbursed),
            total_disbursed_growth_pct=12.0,
            pending_disbursement_amount=float(pending_amount),
            pending_disbursement_count=pending_count,
            this_month_amount=float(this_month_amount),
            this_month_growth_pct=18.0,
            total_disbursements_count=total_count,
        )

    async def get_disbursements(
        self,
        cooperative_id: uuid.UUID,
        search: Optional[str] = None,
        package_type: Optional[str] = None,
        status: Optional[DisbursementStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[DisbursementListItemResponse], int]:
        query = (
            select(Disbursement)
            .options(
                selectinload(Disbursement.farmer),
                selectinload(Disbursement.package).selectinload(Package.disbursements),
                selectinload(Disbursement.package).selectinload(Package.package_farmers),
            )
            .join(Farmer, Disbursement.farmer_id == Farmer.id)
            .join(Package, Disbursement.package_id == Package.id)
            .where(Disbursement.cooperative_id == cooperative_id)
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Farmer.full_name.ilike(term),
                    Package.title.ilike(term),
                    Disbursement.transaction_reference.ilike(term),
                )
            )

        if package_type and package_type.strip():
            query = query.where(Package.category.ilike(
                f"%{package_type.strip()}%"))

        if status:
            query = query.where(Disbursement.status == status)

        if start_date:
            query = query.where(Disbursement.created_at >= start_date)
        if end_date:
            query = query.where(Disbursement.created_at <= end_date)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Disbursement.created_at.desc()).offset(
            offset).limit(page_size)

        result = await self.session.execute(query)
        disbursements = result.scalars().all()
        items = []
        for disbursement in disbursements:
            package = disbursement.package
            progress = self._package_funding_progress(package)
            items.append(
                DisbursementListItemResponse(
                    id=disbursement.id,
                    farmer=FarmerSummarySchema(
                        id=disbursement.farmer.id,
                        full_name=disbursement.farmer.full_name,
                        farmer_code=getattr(disbursement.farmer, "farmer_code", None),
                        avatar_url=getattr(disbursement.farmer, "photo", None),
                    ),
                    package=PackageSummarySchema(
                        package_code=package.package_code,
                        title=package.title,
                        category=str(getattr(package.category, "value", package.category)),
                        package_total_amount=float(package.fund_amount or 0),
                        farmers_count=len(package.package_farmers),
                        current_tranche=progress["current_stage"],
                        tranches=[
                            DisbursementTrancheSchema(**tranche)
                            for tranche in progress["tranches"]
                        ],
                    ),
                    amount=float(disbursement.amount or 0),
                    current_amount_disbursed=self._current_tranche_disbursed_amount(
                        progress
                    ),
                    disbursement_date=self._most_recent_disbursement_date(
                        package, disbursement.disbursement_date
                    ),
                    status=disbursement.status,
                    transaction_reference=disbursement.transaction_reference,
                    notes=disbursement.notes,
                )
            )
        return items, total

    async def get_disbursement_detail(
        self, disbursement_id: uuid.UUID, cooperative_id: uuid.UUID
    ) -> DisbursementDetailResponse:
        query = (
            select(Disbursement)
            .options(
                selectinload(Disbursement.farmer),
                selectinload(Disbursement.package).selectinload(Package.disbursements),
                selectinload(Disbursement.package).selectinload(Package.package_farmers),
                selectinload(Disbursement.recorded_by),
            )
            .where(
                Disbursement.id == disbursement_id,
                Disbursement.cooperative_id == cooperative_id,
            )
        )
        result = await self.session.execute(query)
        disbursement = result.scalars().first()

        if not disbursement:
            raise ValueError("Disbursement record not found.")

        package = disbursement.package
        progress = self._package_funding_progress(package)

        return DisbursementDetailResponse(
            id=disbursement.id,
            farmer={
                "id": disbursement.farmer.id,
                "full_name": disbursement.farmer.full_name,
                "photo": getattr(disbursement.farmer, "photo", None),
            },
            package=PackageSummarySchema(
                package_code=package.package_code,
                title=package.title,
                category=str(getattr(package.category, "value", package.category)),
                package_total_amount=float(package.fund_amount or 0),
                farmers_count=len(package.package_farmers),
                current_tranche=progress["current_stage"],
                tranches=[
                    DisbursementTrancheSchema(**tranche)
                    for tranche in progress["tranches"]
                ],
            ),
            amount=disbursement.amount,
            disbursement_date=disbursement.disbursement_date,
            status=disbursement.status,
            recorded_by_name=_get_user_display_name(disbursement.recorded_by),
            transaction_reference=disbursement.transaction_reference,
            notes=disbursement.notes,
            tranches=[
                DisbursementTrancheSchema(**tranche)
                for tranche in progress["tranches"]
            ],
        )

    async def update_status(
        self,
        disbursement_id: uuid.UUID,
        payload: DisbursementStatusUpdateSchema,
        admin_user: User,
    ) -> Disbursement:
        query = select(Disbursement).where(Disbursement.id == disbursement_id)
        result = await self.session.execute(query)
        disbursement = result.scalars().first()

        if not disbursement:
            raise ValueError("Disbursement record not found.")

        previous_status = disbursement.status
        disbursement.status = payload.status
        disbursement.recorded_by_id = admin_user.id
        if payload.notes:
            disbursement.notes = payload.notes

        if payload.status == DisbursementStatus.DISBURSED:
            disbursement.disbursement_date = datetime.now(timezone.utc)

            # Check if Settlement already exists for this disbursement
            settlement_stmt = select(Settlement).where(
                Settlement.disbursement_id == disbursement.id
            )
            existing_settlement = (await self.session.execute(settlement_stmt)).scalars().first()

            if not existing_settlement:
                # Auto-create Settlement entry
                settlement = Settlement(
                    farmer_id=disbursement.farmer_id,
                    package_id=disbursement.package_id,
                    disbursement_id=disbursement.id,
                    recorded_by_id=admin_user.id,
                    amount_settled=Decimal(str(disbursement.amount)),
                    reference=f"STL-{uuid.uuid4().hex[:10].upper()}",
                    status=SettlementStatus.ONGOING,
                    date_settled=None,
                )
                self.session.add(settlement)

        if previous_status != payload.status:
            package_title = await self.session.scalar(
                select(Package.title).where(Package.id == disbursement.package_id)
            )
            investor_ids = (await self.session.execute(
                select(Investment.investor_id)
                .where(Investment.package_id == disbursement.package_id)
                .distinct()
            )).scalars().all()
            recipients = set(investor_ids)
            recipients.add(disbursement.cooperative_id)
            recipients.discard(admin_user.id)
            for recipient_id in recipients:
                add_notification(
                    self.session,
                    recipient_id,
                    "Farmer disbursement updated",
                    f"A disbursement for package '{package_title or 'your package'}' is now {payload.status.value.title()}.",
                    "DISBURSEMENT_STATUS",
                    actor_id=admin_user.id,
                    entity_type="disbursement",
                    entity_id=disbursement.id,
                    link=f"/disbursements/{disbursement.id}",
                )

        await self.session.commit()
        await self.session.refresh(disbursement)
        return disbursement
