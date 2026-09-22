import uuid
from datetime import date, datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.investment_model import Investment, InvestmentStatus
from app.models.package_model import Package
from app.models.user_model import User
from app.schemas.investment_schema import (
    CooperativeInvestmentDetail,
    CooperativeInvestmentList,
    CooperativeInvestmentSummary,
    Metrics,
    PaginatedCooperativeInvestments,
    SettlementStatus,
)


class CooperativeInvestmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_summary(self, cooperative_id: uuid.UUID) -> CooperativeInvestmentSummary:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        async def fetch_period_stats(start_date=None, end_date=None):
            stmt = (
                select(
                    func.coalesce(func.sum(Investment.amount),
                                  0.0).label("total"),
                    func.coalesce(
                        func.sum(case(
                            (Investment.status == InvestmentStatus.ACTIVE, Investment.amount), else_=0.0)),
                        0.0,
                    ).label("active"),
                    func.coalesce(
                        func.sum(
                            case((Investment.status == InvestmentStatus.ACTIVE,
                                  Investment.expected_farmer_payout), else_=0.0)
                        ),
                        0.0,
                    ).label("settlement"),
                    func.coalesce(
                        func.sum(case(
                            (Investment.status == InvestmentStatus.OVERDUE, Investment.amount), else_=0.0)),
                        0.0,
                    ).label("overdue"),
                )
                .join(Package, Investment.package_id == Package.id)
                .where(Package.cooperative_id == cooperative_id)
            )

            if start_date:
                stmt = stmt.where(Investment.created_at >= start_date)
            if end_date:
                stmt = stmt.where(Investment.created_at < end_date)

            res = await self.db.execute(stmt)
            return res.one()

        current = await fetch_period_stats()
        prev = await fetch_period_stats(start_date=sixty_days_ago, end_date=thirty_days_ago)

        def calc_trend(curr_val, prev_val):
            if not prev_val or prev_val == 0:
                return 0.0
            return round(((curr_val - prev_val) / prev_val) * 100, 1)

        return CooperativeInvestmentSummary(
            total_invested=Metrics(
                value=float(current.total),
                trend_percentage=calc_trend(current.total, prev.total),
            ),
            active_investments=Metrics(
                value=float(current.active),
                trend_percentage=calc_trend(current.active, prev.active),
            ),
            expected_settlement=Metrics(
                value=float(current.settlement),
                trend_percentage=calc_trend(
                    current.settlement, prev.settlement),
            ),
            overdue_investments=Metrics(
                value=float(current.overdue),
                trend_percentage=calc_trend(current.overdue, prev.overdue),
            ),
        )

    async def get_cooperative_investments(
        self,
        cooperative_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        search: str | None = None,
        category: str | None = None,
        status_filter: InvestmentStatus | None = None,
    ) -> PaginatedCooperativeInvestments:
        base_query = (
            select(Investment)
            .join(Package, Investment.package_id == Package.id)
            .join(User, Investment.investor_id == User.id)
            .where(Package.cooperative_id == cooperative_id)
        )

        if status_filter:
            base_query = base_query.where(Investment.status == status_filter)

        if category:
            base_query = base_query.where(
                Package.category.ilike(f"%{category}%"))

        if search:
            search_fmt = f"%{search}%"
            base_query = base_query.where(
                or_(
                    User.first_name.ilike(search_fmt),
                    User.last_name.ilike(search_fmt),
                    User.phone_number.ilike(search_fmt),
                    Package.title.ilike(search_fmt),
                    Package.category.ilike(search_fmt),
                )
            )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        offset = (page - 1) * size
        items_stmt = (
            base_query.options(
                selectinload(Investment.package),
                selectinload(Investment.investor),
            )
            .order_by(Investment.created_at.desc())
            .offset(offset)
            .limit(size)
        )

        items_res = await self.db.execute(items_stmt)
        investments = items_res.scalars().all()

        formatted_items = [
            CooperativeInvestmentList(
                id=inv.id,
                investor_id_code=getattr(
                    inv.investor, "display_id", f"LN-25-{str(inv.investor_id)[:5]}"
                ),
                investor_name=f"{inv.investor.first_name or ''} {inv.investor.last_name or ''}".strip(
                )
                or inv.investor.email,
                investor_avatar=getattr(inv.investor, "avatar_url", None),
                package_title=inv.package.title,
                package_category=getattr(
                    inv.package, "category", "Crop Farming"
                ),
                amount=inv.amount,
                date_invested=inv.created_at,
                status=inv.status,
            )
            for inv in investments
        ]

        return PaginatedCooperativeInvestments(
            total=total, page=page, size=size, items=formatted_items
        )

    async def get_investment_detail(
        self, investment_id: uuid.UUID, cooperative_id: uuid.UUID
    ) -> CooperativeInvestmentDetail:
        stmt = (
            select(Investment)
            .options(
                selectinload(Investment.package).selectinload(
                    Package.package_farmers),
                selectinload(Investment.investor),
            )
            .join(Package, Investment.package_id == Package.id)
            .where(
                Investment.id == investment_id,
                Package.cooperative_id == cooperative_id,
            )
        )

        res = await self.db.execute(stmt)
        inv = res.scalars().first()

        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investment detail record not found.",
            )

        package = inv.package
        package_farmers = getattr(package, "package_farmers", []) or []

        if package_farmers:
            avg_progress = sum(getattr(pf, "progress_percentage", 0.0)
                               for pf in package_farmers) / len(package_farmers)
        else:
            avg_progress = 0.0

        payback_date = getattr(package, "expected_payback_date", None)
        today = date.today()

        if inv.status == InvestmentStatus.REPAID:
            settlement_status = SettlementStatus.COMPLETED
        elif inv.status == InvestmentStatus.OVERDUE or (payback_date and payback_date < today):
            settlement_status = SettlementStatus.OVERDUE
        else:
            settlement_status = SettlementStatus.PENDING

        return CooperativeInvestmentDetail(
            id=inv.id,
            investor_id_code=getattr(
                inv.investor, "display_id", f"ID-{str(inv.investor_id)[:5]}"
            ),
            investor_name=f"{inv.investor.first_name or ''} {inv.investor.last_name or ''}".strip(
            )
            or inv.investor.email,
            investor_avatar=getattr(inv.investor, "avatar_url", None),
            investor_is_active=getattr(inv.investor, "is_active", True),
            package_title=package.title,
            package_category=getattr(package, "category", "Crop Farming"),
            amount_invested=inv.amount,
            date_invested=inv.created_at,
            payment_method=getattr(inv, "payment_method", "Bank Transfer"),
            transaction_reference=getattr(inv, "transaction_reference", None),


            farming_progress=round(avg_progress, 2),
            farming_cycle=getattr(package, "farming_cycle", "N/A"),
            farmers_supported=len(package_farmers),

            expected_settlement_date=payback_date or today,
            expected_settlement_amount=inv.expected_farmer_payout,
            settlement_status=settlement_status,

            status=inv.status,
        )
