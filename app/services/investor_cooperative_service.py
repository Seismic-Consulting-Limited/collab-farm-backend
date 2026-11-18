import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile_model import CooperativeProfile
from app.models.user_model import User, UserRole, VerificationStatus
from app.schemas.investor_dashboard_schema import (
    InvestorCooperativeItem,
    InvestorCooperativesResponse,
)


class InvestorCooperativeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_cooperatives(
        self, page: int = 1, page_size: int = 12
    ) -> InvestorCooperativesResponse:
        filters = (
            User.role == UserRole.COOPERATIVE,
            User.verification_status == VerificationStatus.APPROVED,
        )
        total = await self.db.scalar(
            select(func.count(CooperativeProfile.id))
            .join(User, CooperativeProfile.user_id == User.id)
            .where(*filters)
        ) or 0

        result = await self.db.execute(
            select(CooperativeProfile, User.id)
            .join(User, CooperativeProfile.user_id == User.id)
            .where(*filters)
            .order_by(CooperativeProfile.cooperative_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [
            InvestorCooperativeItem(
                id=user_id,
                cooperative_name=profile.cooperative_name,
                year_established=profile.year_established,
                registration_number=profile.registration_number,
                phone_number=profile.phone_number,
                address=profile.address,
                lga=profile.lga,
                state=profile.state,
            )
            for profile, user_id in result.all()
        ]

        return InvestorCooperativesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total else 0,
        )
