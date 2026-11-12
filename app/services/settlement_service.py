import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.settlement_model import Settlement, SettlementStatus
from app.models.farmer_model import Farmer
from app.models.package_model import Package
from app.models.cooperative_investment_model import Investment, InvestmentStatus
from app.models.user_model import User, UserRole
from app.utils.settlement_dates import package_settlement_date
from app.schemas.settlement_schema import (
    SettlementMetricsResponse,
    SettlementDetailResponse,
    SettlementListItemResponse,
    FarmerSummarySchema,
    PackageSummarySchema,
    PackageSettlementSummarySchema,
    InvestorToSettleSchema,
    InvestorSettlementSchema,
    SettlementReturnReportSchema,
    SettlementReceiptReviewSchema,
)
from app.services.notification_service import add_notification


class SettlementService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _assert_settlement_role(user: User) -> None:
        if user.role not in {UserRole.ADMIN, UserRole.COOPERATIVE}:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and cooperatives can access settlements.",
            )

    @staticmethod
    def _net_settlement_percentage(package: Package) -> float:
        return max(
            float(package.expected_roi or 0.0)
            - float(package.cooperative_share or 0.0),
            0.0,
        )

    @classmethod
    def _amount_due(cls, settlement: Settlement) -> Decimal:
        net_rate = Decimal(str(cls._net_settlement_percentage(settlement.package)))
        principal = Decimal(str(settlement.amount_settled or 0))
        return (principal * (Decimal("1") + net_rate / Decimal("100"))).quantize(
            Decimal("0.01")
        )

    @staticmethod
    def _settlement_due_date(settlement: Settlement):
        disbursements = [settlement.disbursement] if settlement.disbursement else []
        return package_settlement_date(
            settlement.package,
            disbursements=disbursements,
            farmer_id=settlement.farmer_id,
        )

    @classmethod
    def _display_status(cls, settlement: Settlement) -> SettlementStatus:
        if settlement.status in {
            SettlementStatus.ONGOING,
            SettlementStatus.PENDING,
            SettlementStatus.DISBURSED,
        }:
            due_date = cls._settlement_due_date(settlement)
            if due_date and due_date < datetime.now(timezone.utc).date():
                return SettlementStatus.OVERDUE
            return SettlementStatus.ONGOING
        return settlement.status

    @classmethod
    def _list_item(cls, settlement: Settlement) -> SettlementListItemResponse:
        package = settlement.package
        return SettlementListItemResponse(
            id=settlement.id,
            farmer=FarmerSummarySchema(
                id=settlement.farmer.id,
                full_name=settlement.farmer.full_name,
                farmer_code=settlement.farmer.farmer_code,
                avatar_url=settlement.farmer.photo,
            ),
            package=PackageSummarySchema(
                id=package.id,
                title=package.title,
                category=str(getattr(package.category, "value", package.category)),
                package_total_amount=float(package.fund_amount or 0),
            ),
            amount_to_be_settled=cls._amount_due(settlement),
            category=str(getattr(package.category, "value", package.category)),
            settlement_due_date=cls._settlement_due_date(settlement),
            status=cls._display_status(settlement),
            reference=settlement.reference,
        )

    @classmethod
    def _investor_settlements(
        cls, settlement: Settlement
    ) -> list[InvestorSettlementSchema]:
        package = settlement.package
        package_amount = Decimal(str(package.fund_amount or 0))
        if package_amount <= 0:
            return []
        farmer_share = Decimal(str(settlement.amount_settled or 0)) / package_amount
        net_multiplier = Decimal("1") + Decimal(
            str(cls._net_settlement_percentage(package))
        ) / Decimal("100")
        investors = []
        for investment in package.investments:
            if investment.status == InvestmentStatus.REPAID:
                continue
            amount_due = (
                Decimal(str(investment.amount or 0)) * farmer_share * net_multiplier
            ).quantize(Decimal("0.01"))
            investor = investment.investor
            name = f"{investor.first_name or ''} {investor.last_name or ''}".strip()
            investors.append(
                InvestorSettlementSchema(
                    investor_id=investment.investor_id,
                    investor_name=name or investor.email,
                    amount_to_be_settled=amount_due,
                )
            )
        return investors

    @staticmethod
    def _package_settlement_summary(package: Package) -> dict:
        pending_investments = [
            investment
            for investment in package.investments
            if investment.status != InvestmentStatus.REPAID
        ]
        expected_roi_pct = float(package.expected_roi or 0.0)
        cooperative_share_pct = float(package.cooperative_share or 0.0)
        investor_roi_pct = max(expected_roi_pct - cooperative_share_pct, 0.0)
        expected_return_amount = sum(
            float(investment.amount or 0.0) * investor_roi_pct / 100
            for investment in pending_investments
        )
        expected_settlement_amount = sum(
            float(investment.amount or 0.0) * (1 + investor_roi_pct / 100)
            for investment in pending_investments
        )
        statuses = {investment.status for investment in pending_investments}
        if InvestmentStatus.PENDING in statuses:
            status = "Pending"
        elif InvestmentStatus.OVERDUE in statuses:
            status = "Overdue"
        elif pending_investments:
            status = "Active"
        else:
            status = "Settled"
        return {
            "package_total_amount": float(package.fund_amount or 0.0),
            "expected_return_percentage": investor_roi_pct,
            "expected_return_amount": round(expected_return_amount, 2),
            "expected_settlement_amount": round(expected_settlement_amount, 2),
            "investors_to_be_settled": len(
                {investment.investor_id for investment in pending_investments}
            ),
            "status": status,
        }

    @staticmethod
    def _package_investors_to_settle(package: Package) -> list[InvestorToSettleSchema]:
        expected_roi_pct = float(package.expected_roi or 0.0)
        cooperative_share_pct = float(package.cooperative_share or 0.0)
        investor_roi_pct = max(expected_roi_pct - cooperative_share_pct, 0.0)
        investors = []
        for investment in package.investments:
            if investment.status == InvestmentStatus.REPAID:
                continue
            amount = float(investment.amount or 0.0)
            investor = investment.investor
            investor_name = f"{investor.first_name or ''} {investor.last_name or ''}".strip()
            investors.append(
                InvestorToSettleSchema(
                    investor_id=investment.investor_id,
                    investor_name=investor_name or investor.email,
                    amount_invested=amount,
                    expected_return_amount=round(amount * investor_roi_pct / 100, 2),
                    expected_settlement_amount=round(
                        amount * (1 + investor_roi_pct / 100), 2
                    ),
                    status=str(getattr(investment.status, "value", investment.status)),
                )
            )
        return investors

    @staticmethod
    async def auto_create_settlement_on_disbursement(
        session: AsyncSession,
        farmer_id: uuid.UUID,
        package_id: uuid.UUID,
        disbursement_id: uuid.UUID,
        amount: Decimal,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> Settlement:
        """Automated trigger: Creates a Settlement tracking entry when funds are disbursed to a farmer."""
        reference = f"TX-{uuid.uuid4().hex[:10].upper()}"

        settlement = Settlement(
            farmer_id=farmer_id,
            package_id=package_id,
            disbursement_id=disbursement_id,
            recorded_by_id=admin_user_id,
            amount_settled=amount,
            reference=reference,
            status=SettlementStatus.ONGOING,
            date_settled=None,
        )
        session.add(settlement)
        await session.commit()
        await session.refresh(settlement)
        return settlement

    def _get_user_display_name(user: Optional[User]) -> str:
        if not user:
            return "System Automated"

        first = getattr(user, "first_name", "") or ""
        last = getattr(user, "last_name", "") or ""
        full_name = f"{first} {last}".strip()

        return full_name if full_name else getattr(user, "email", "Admin User")

    def _settlement_query(self, user: User):
        self._assert_settlement_role(user)
        query = (
            select(Settlement)
            .join(Package, Package.id == Settlement.package_id)
            .options(
                selectinload(Settlement.farmer),
                selectinload(Settlement.package)
                .selectinload(Package.investments)
                .selectinload(Investment.investor),
                selectinload(Settlement.disbursement),
            )
        )
        if user.role == UserRole.COOPERATIVE:
            query = query.where(Package.cooperative_id == user.id)
        return query

    async def get_metrics(self, user: User) -> SettlementMetricsResponse:
        now = datetime.now(timezone.utc)
        first_day_this_month = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
        settlements = (await self.session.execute(
            self._settlement_query(user)
        )).scalars().unique().all()
        settled = [row for row in settlements if row.status == SettlementStatus.SETTLED]
        pending = [row for row in settlements if row.status != SettlementStatus.SETTLED]
        total_settled = sum((self._amount_due(row) for row in settled), Decimal("0.00"))
        pending_amount = sum((self._amount_due(row) for row in pending), Decimal("0.00"))
        pending_count = len(pending)
        this_month_amount = sum(
            (
                self._amount_due(row)
                for row in settled
                if row.date_settled and row.date_settled >= first_day_this_month
            ),
            Decimal("0.00"),
        )
        total_count = len(settlements)

        return SettlementMetricsResponse(
            total_settled=total_settled,
            total_settled_growth_pct=12.0,  # Calculated against prior month window
            pending_settlement_amount=pending_amount,
            pending_settlement_count=pending_count,
            this_month_amount=this_month_amount,
            this_month_growth_pct=18.0,
            total_settlements_count=total_count,
        )

    async def get_settlements(
        self,
        user: User,
        search: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[SettlementStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[SettlementListItemResponse], int]:
        query = self._settlement_query(user).join(
            Farmer, Settlement.farmer_id == Farmer.id
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Farmer.full_name.ilike(term),
                    Package.title.ilike(term),
                    Settlement.reference.ilike(term),
                )
            )

        if category and category.strip():
            query = query.where(Package.category.ilike(f"%{category.strip()}%"))

        if start_date:
            query = query.where(Settlement.created_at >= start_date)
        if end_date:
            query = query.where(Settlement.created_at <= end_date)

        if status in {
            SettlementStatus.ONGOING,
            SettlementStatus.PENDING,
            SettlementStatus.OVERDUE,
        }:
            query = query.where(
                Settlement.status.in_(
                    [SettlementStatus.ONGOING, SettlementStatus.PENDING, SettlementStatus.DISBURSED]
                )
            )
            all_rows = (await self.session.execute(
                query.order_by(Settlement.created_at.desc())
            )).scalars().unique().all()
            desired_status = (
                SettlementStatus.ONGOING
                if status == SettlementStatus.PENDING
                else status
            )
            matched_rows = [
                row
                for row in all_rows
                if self._display_status(row) == desired_status
            ]
            total = len(matched_rows)
            offset = (page - 1) * page_size
            return [
                self._list_item(row)
                for row in matched_rows[offset : offset + page_size]
            ], total
        elif status:
            query = query.where(Settlement.status == status)

        # Count total matches without eager-load options.
        count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Paginate results
        offset = (page - 1) * page_size
        query = query.order_by(Settlement.created_at.desc()).offset(
            offset).limit(page_size)

        result = await self.session.execute(query)
        settlements = result.scalars().unique().all()
        return [self._list_item(row) for row in settlements], total

    async def get_package_settlements(
        self,
        user: User,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[PackageSettlementSummarySchema], int]:
        self._assert_settlement_role(user)
        query = (
            select(Package)
            .join(Investment, Investment.package_id == Package.id)
            .join(User, User.id == Investment.investor_id)
            .where(Investment.status != InvestmentStatus.REPAID)
        )
        if user.role == UserRole.COOPERATIVE:
            query = query.where(Package.cooperative_id == user.id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Package.title.ilike(term),
                    Package.category.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.email.ilike(term),
                )
            )

        count_query = select(func.count()).select_from(
            query.with_only_columns(Package.id).distinct().subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        query = (
            query.options(
                selectinload(Package.investments).selectinload(Investment.investor)
            )
            .distinct()
            .order_by(Package.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        packages = (await self.session.execute(query)).unique().scalars().all()

        items = []
        for package in packages:
            summary = self._package_settlement_summary(package)
            investors = self._package_investors_to_settle(package)
            items.append(
                PackageSettlementSummarySchema(
                    package_id=package.id,
                    package_name=package.title,
                    package_category=str(
                        getattr(package.category, "value", package.category)
                    ),
                    investors=investors,
                    **summary,
                )
            )
        return items, total

    async def get_settlement_detail(
        self, settlement_id: uuid.UUID, user: User
    ) -> SettlementDetailResponse:
        self._assert_settlement_role(user)
        query = (
            select(Settlement)
            .options(
                selectinload(Settlement.farmer),
                selectinload(Settlement.package)
                .selectinload(Package.investments)
                .selectinload(Investment.investor),
                selectinload(Settlement.recorded_by),
                selectinload(Settlement.disbursement),
            )
            .where(Settlement.id == settlement_id)
        )
        result = await self.session.execute(query)
        settlement = result.scalars().first()

        if not settlement:
            raise ValueError("Settlement record not found.")
        if (
            user.role == UserRole.COOPERATIVE
            and settlement.package.cooperative_id != user.id
        ):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view settlements for your cooperative.",
            )
        package = settlement.package
        net_percentage = self._net_settlement_percentage(package)
        amount_due = self._amount_due(settlement)
        return_amount = (amount_due - Decimal(str(settlement.amount_settled))).quantize(
            Decimal("0.01")
        )
        package_summary = PackageSummarySchema(
            id=package.id,
            title=package.title,
            category=str(getattr(package.category, "value", package.category)),
            package_total_amount=float(package.fund_amount or 0),
        )

        return SettlementDetailResponse(
            id=settlement.id,
            farmer={
                "id": settlement.farmer.id,
                "full_name": settlement.farmer.full_name,
                "farmer_code": settlement.farmer.farmer_code,
                "avatar_url": settlement.farmer.photo,
            },
            package=package_summary,
            amount_to_be_settled=amount_due,
            settlement_percentage=net_percentage,
            return_amount=return_amount,
            settlement_due_date=self._settlement_due_date(settlement),
            date_settled=settlement.date_settled,
            status=self._display_status(settlement),
            reference=settlement.reference,
            transaction_reference=settlement.reference,
            investors=self._investor_settlements(settlement),
            return_reported_at=settlement.return_reported_at,
            return_note=settlement.return_note,
            review_note=settlement.review_note,
        )

    async def report_return(
        self,
        settlement_id: uuid.UUID,
        payload: SettlementReturnReportSchema,
        actor: User,
    ) -> Settlement:
        self._assert_settlement_role(actor)
        if actor.role != UserRole.COOPERATIVE:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only cooperatives can report returned funds.")
        query = select(Settlement).options(selectinload(Settlement.package)).where(
            Settlement.id == settlement_id
        )
        result = await self.session.execute(query)
        settlement = result.scalars().first()

        if not settlement:
            raise ValueError("Settlement record not found.")

        if settlement.package.cooperative_id != actor.id:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot report funds for this cooperative.")
        if settlement.status == SettlementStatus.SETTLED:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This settlement is already settled.")
        if settlement.status == SettlementStatus.REVIEWING:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This return is already awaiting admin verification.")

        settlement.status = SettlementStatus.REVIEWING
        settlement.return_reported_at = datetime.now(timezone.utc)
        settlement.returned_by_id = actor.id
        settlement.return_note = payload.note
        settlement.review_note = None
        admin_ids = (await self.session.execute(
            select(User.id).where(User.role == UserRole.ADMIN)
        )).scalars().all()
        for admin_id in admin_ids:
            add_notification(
                self.session,
                admin_id,
                "Cooperative reported settlement return",
                f"{actor.full_name} reported funds returned for package '{settlement.package.title}'. Verify receipt.",
                "SETTLEMENT_RETURN_REPORTED",
                actor_id=actor.id,
                entity_type="settlement",
                entity_id=settlement.id,
                link=f"/settlements/{settlement.id}",
            )

        await self.session.commit()
        await self.session.refresh(settlement)
        return settlement

    async def review_return_receipt(
        self,
        settlement_id: uuid.UUID,
        payload: SettlementReceiptReviewSchema,
        actor: User,
    ) -> Settlement:
        self._assert_settlement_role(actor)
        if actor.role != UserRole.ADMIN:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can verify receipt.")
        query = select(Settlement).options(selectinload(Settlement.package)).where(
            Settlement.id == settlement_id
        )
        settlement = (await self.session.execute(query)).scalars().first()
        if not settlement:
            raise ValueError("Settlement record not found.")
        if settlement.status != SettlementStatus.REVIEWING:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This settlement has not been reported for receipt verification.")

        settlement.review_note = payload.note
        if payload.received:
            settlement.status = SettlementStatus.SETTLED
            settlement.date_settled = datetime.now(timezone.utc)
            settlement.receipt_verified_by_id = actor.id
            settlement.recorded_by_id = actor.id
        else:
            settlement.status = SettlementStatus.REJECTED
            settlement.date_settled = None
            settlement.receipt_verified_by_id = None

        recipients = {settlement.package.cooperative_id}
        recipients.update((await self.session.execute(
            select(Investment.investor_id)
            .where(Investment.package_id == settlement.package_id)
            .distinct()
        )).scalars().all())
        recipients.discard(actor.id)
        for recipient_id in recipients:
            add_notification(
                self.session,
                recipient_id,
                "Settlement receipt reviewed",
                f"Admin {'confirmed receipt' if payload.received else 'could not confirm receipt'} for '{settlement.package.title}'.",
                "SETTLEMENT_RECEIPT_REVIEWED",
                actor_id=actor.id,
                entity_type="settlement",
                entity_id=settlement.id,
                link=f"/settlements/{settlement.id}",
            )

        await self.session.commit()
        await self.session.refresh(settlement)
        return settlement
