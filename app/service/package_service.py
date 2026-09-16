import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.packageModel import (
    FarmerPackageStatus,
    Investment,
    Package,
    PackageCategory,
    PackageFarmer,
    PackageStatus,
    PackageType,
)
from app.models.userModel import User, UserRole
from app.schemas.packageschema import (
    AssignFarmerSchema,
    PackageCreate,
    PackageDetailRead,
    PackageFarmerDetail,
    PackageFinancialSummary,
    PackageInvestorDetail,
    PackageInvestorResponse,
    PackageRead,
    PackageUpdate,
)


class PackageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_package(self, user: User, payload: PackageCreate) -> Package:
        if user.role != UserRole.COOPERATIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Cooperatives can create investment packages.",
            )

        package = Package(
            cooperative_id=user.id,
            **payload.model_dump(),
        )
        self.db.add(package)
        await self.db.commit()
        await self.db.refresh(package)
        return package

    async def assign_farmer(
        self, user: User, package_id: uuid.UUID, payload: AssignFarmerSchema
    ) -> PackageFarmer:
        result = await self.db.execute(select(Package).where(Package.id == package_id))
        package = result.scalars().first()

        if not package or package.cooperative_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package not found or unauthorized.",
            )

        assignment = PackageFarmer(
            package_id=package_id,
            farmer_id=payload.farmer_id,
            allocated_amount=payload.allocated_amount,
            payout_date=payload.payout_date,
            payback_date=payload.payback_date or package.expected_payback_date,
            status=FarmerPackageStatus.PENDING,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def get_package_details(self, package_id: uuid.UUID) -> PackageDetailRead:
        query = (
            select(Package)
            .options(
                selectinload(Package.package_farmers),
                selectinload(Package.investments),
            )
            .where(Package.id == package_id)
        )
        result = await self.db.execute(query)
        package = result.scalars().first()

        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investment package not found.",
            )

        total_invested = sum(inv.amount for inv in package.investments)
        total_disbursed = sum(
            pf.allocated_amount
            for pf in package.package_farmers
            if pf.status == FarmerPackageStatus.DISBURSED
        )
        remaining_balance = total_invested - total_disbursed

        return PackageDetailRead(
            id=package.id,
            cooperative_id=package.cooperative_id,
            title=package.title,
            package_type=package.package_type,
            category=package.category,
            farming_cycle=package.farming_cycle,
            short_description=package.short_description,
            fund_amount=package.fund_amount,
            tenure_months=package.tenure_months,
            expected_payback_date=package.expected_payback_date,
            expected_roi=package.expected_roi,
            cooperative_share=package.cooperative_share,
            status=package.status,
            financial_summary=PackageFinancialSummary(
                total_money_invested=total_invested,
                total_disbursed_to_farmers=total_disbursed,
                remaining_balance=remaining_balance,
            ),
            assigned_farmers=[
                PackageFarmerDetail.model_validate(pf) for pf in package.package_farmers
            ],
            investors=[
                PackageInvestorDetail.model_validate(inv) for inv in package.investments
            ],
        )

    async def get_package_investors(
        self, package_id: uuid.UUID
    ) -> List[PackageInvestorResponse]:
        query = (
            select(Investment)
            .options(selectinload(Investment.investor))
            .where(Investment.package_id == package_id)
        )
        result = await self.db.execute(query)
        investments = result.scalars().all()

        return [
            PackageInvestorResponse(
                id=inv.id,
                investor_id=inv.investor_id,
                investor_name=f"{inv.investor.first_name or ''} {inv.investor.last_name or ''}".strip(
                )
                or inv.investor.email,
                email=inv.investor.email,
                investor_type=inv.investor.investor_type,
                amount=inv.amount,
                invested_at=inv.created_at,
                payback_due_date=inv.payback_due_date,
            )
            for inv in investments
        ]

    async def get_all_packages(
        self,
        category: Optional[PackageCategory] = None,
        package_type: Optional[PackageType] = None,
        status_filter: Optional[PackageStatus] = None,
        cooperative_id: Optional[uuid.UUID] = None,
    ) -> List[PackageRead]:
        query = select(Package)

        if category:
            query = query.where(Package.category == category)
        if package_type:
            query = query.where(Package.package_type == package_type)
        if status_filter:
            query = query.where(Package.status == status_filter)
        if cooperative_id:
            query = query.where(Package.cooperative_id == cooperative_id)

        query = query.order_by(Package.created_at.desc())

        result = await self.db.execute(query)
        packages = result.scalars().all()

        return [PackageRead.model_validate(pkg) for pkg in packages]

    async def update_package(
        self, user: User, package_id: uuid.UUID, payload: PackageUpdate
    ) -> Package:
        package = await self.db.get(Package, package_id)

        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No package with ID '{package_id}' was found.",
            )

        if package.cooperative_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this package.",
            )

        update_data = payload.model_dump(exclude_unset=True)

        target_type = update_data.get("package_type", package.package_type)
        target_amount = update_data.get("fund_amount", package.fund_amount)

        min_amounts = {
            PackageType.STARTER: 1_000_000.0,
            PackageType.GROWTH: 3_000_000.0,
            PackageType.COMMERCIAL: 5_000_000.0,
        }
        min_required = min_amounts.get(target_type, 0.0)
        if target_amount < min_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fund amount for {target_type.value} must be at least ₦{min_required:,.2f}",
            )

        for key, value in update_data.items():
            setattr(package, key, value)

        await self.db.commit()
        await self.db.refresh(package)

        return package
