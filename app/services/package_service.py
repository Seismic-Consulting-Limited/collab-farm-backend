import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cooperative_investment_model import Investment
from app.models.disbursement_model import Disbursement, DisbursementStatus
from app.models.farmer_model import Farmer
from app.models.package_model import (
    FarmerPackageStatus,
    Package,
    PackageCategory,
    PackageFarmer,
    PackageStatus,
    PackageType,
)
from app.models.user_model import User, UserRole
from app.schemas.package_schema import (
    AssignFarmerSchema,
    PackageCreate,
    PackageDetailRead,
    PackageFarmerDetail,
    PackageFinancialSummary,
    PackageInvestorDetail,
    PackageInvestorResponse,
    PackageRead,
    PackageUpdate,
    WhatsIncludedItem,
)


class PackageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _calculate_settlement(self, amount: float, roi_pct: float) -> float:
        """Calculate expected settlement amount dynamically in the service layer."""
        if not amount or amount <= 0:
            return 0.0
        return round(amount + (amount * (roi_pct / 100.0)), 2)
    
    def _parse_whats_included(self, raw_data: Optional[list]) -> List[WhatsIncludedItem]:
        """Parse raw stored JSON, dicts, or strings into List[WhatsIncludedItem]."""
        if not raw_data:
            return [
                WhatsIncludedItem(item="Seeds", amount=0.0),
                WhatsIncludedItem(item="Fertilizer (basic)", amount=0.0),
                WhatsIncludedItem(item="Land Preparation", amount=0.0),
                WhatsIncludedItem(item="Basic tools and inputs", amount=0.0),
            ]

        parsed: List[WhatsIncludedItem] = []
        for entry in raw_data:
            if isinstance(entry, WhatsIncludedItem):
                parsed.append(entry)
            elif isinstance(entry, dict):
                item_name = entry.get("item") or entry.get("name") or entry.get("input") or "Item"
                amt = float(entry.get("amount", 0.0) or 0.0)
                parsed.append(WhatsIncludedItem(item=item_name, amount=amt))
            elif isinstance(entry, str):
                parsed.append(WhatsIncludedItem(item=entry, amount=0.0))
        return parsed

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

    async def assign_farmers(
        self, user: User, package_id: uuid.UUID, payload: AssignFarmerSchema
    ) -> List[PackageFarmer]:
        # 1. Verify Package Ownership
        result = await self.db.execute(select(Package).where(Package.id == package_id))
        package = result.scalars().first()

        if not package or package.cooperative_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package not found or unauthorized.",
            )

        # 2. Fetch Farmer Profiles in Batch
        unique_farmer_ids = list(set(payload.farmer_ids))
        farmers_stmt = select(Farmer).where(Farmer.id.in_(unique_farmer_ids))
        farmers_res = await self.db.execute(farmers_stmt)
        farmers = list(farmers_res.scalars().all())

        if not farmers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="None of the specified farmer profiles were found.",
            )

        farmer_map = {farmer.id: farmer for farmer in farmers}
        found_farmer_ids = list(farmer_map.keys())

        # 3. Filter Out Farmers Already Assigned to This Package
        existing_stmt = select(PackageFarmer.farmer_id).where(
            PackageFarmer.package_id == package_id,
            PackageFarmer.farmer_id.in_(found_farmer_ids),
        )
        existing_res = await self.db.execute(existing_stmt)
        already_assigned_ids = set(existing_res.scalars().all())

        new_farmer_ids = [fid for fid in found_farmer_ids if fid not in already_assigned_ids]

        if not new_farmer_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All selected farmers are already assigned to this package.",
            )

        # 4. Create PackageFarmer & Disbursement Records for Each Farmer
        new_assignment_ids = []

        for farmer_id in new_farmer_ids:
            farmer_record = farmer_map[farmer_id]
            farmer_user_id = getattr(farmer_record, "user_id", farmer_record.id)

            # Create assignment entry
            assignment = PackageFarmer(
                package_id=package_id,
                farmer_id=farmer_id,
                allocated_amount=package.fund_amount,
                tenure_months=package.tenure_months,
                expected_roi=package.expected_roi,
                status=FarmerPackageStatus.PENDING,
            )
            self.db.add(assignment)
            await self.db.flush()  # Populates assignment.id
            new_assignment_ids.append(assignment.id)

            # Auto-generate unique disbursement reference per farmer
            tx_ref = f"DSB-{str(package_id)[:4].upper()}-{str(farmer_id)[:4].upper()}-{uuid.uuid4().hex[:6].upper()}"

            disbursement = Disbursement(
                package_id=package_id,
                cooperative_id=package.cooperative_id,
                farmer_id=farmer_user_id,
                recorded_by_id=user.id,
                amount=float(package.fund_amount),
                transaction_reference=tx_ref,
                status=DisbursementStatus.PENDING,
                notes=f"Auto-generated pending disbursement for package '{package.title}'",
            )
            self.db.add(disbursement)

        # 5. Commit Bulk Database Operations
        await self.db.commit()

        # 6. Eager-load relationships for response serialization
        query = (
            select(PackageFarmer)
            .options(
                selectinload(PackageFarmer.farmer),
                selectinload(PackageFarmer.package),
            )
            .where(PackageFarmer.id.in_(new_assignment_ids))
        )
        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def get_all_packages(
        self,
        user: User,
        category: Optional[PackageCategory] = None,
        package_type: Optional[PackageType] = None,
        status_filter: Optional[PackageStatus] = None,
        cooperative_id: Optional[uuid.UUID] = None,
    ) -> List[PackageRead]:
        query = (
            select(Package)
            .options(
                selectinload(Package.cooperative).selectinload(User.cooperative_profile)
            )
        )

        if user.role == UserRole.COOPERATIVE:
            query = query.where(Package.cooperative_id == user.id)
        elif cooperative_id:
            query = query.where(Package.cooperative_id == cooperative_id)

        if category:
            query = query.where(Package.category == category)
        if package_type:
            query = query.where(Package.package_type == package_type)
        if status_filter:
            query = query.where(Package.status == status_filter)

        query = query.order_by(Package.created_at.desc())

        result = await self.db.execute(query)
        packages = result.scalars().all()

        package_reads = []
        for pkg in packages:
            fund_amt = float(pkg.fund_amount or 0.0)
            roi_val = float(pkg.expected_roi or 0.0)
            settlement_amt = self._calculate_settlement(fund_amt, roi_val)

            coop_name = (
                pkg.cooperative.cooperative_profile.cooperative_name
                if pkg.cooperative and getattr(pkg.cooperative, "cooperative_profile", None)
                else getattr(pkg, "cooperative_name", None)
            )

            package_reads.append(
                PackageRead(
                    id=pkg.id,
                    cooperative_id=pkg.cooperative_id,
                    cooperative_name=coop_name,
                    title=pkg.title,
                    package_type=pkg.package_type,
                    category=pkg.category,
                    fund_amount=fund_amt,
                    farming_cycle=pkg.farming_cycle,
                    short_description=pkg.short_description,
                    tenure_months=pkg.tenure_months,
                    expected_payback_date=pkg.expected_payback_date,
                    expected_roi=roi_val,
                    cooperative_share=float(pkg.cooperative_share or 0.0),
                    expected_settlement_amount=settlement_amt,
                    whats_included=self._parse_whats_included(pkg.whats_included),
                    status=pkg.status,
                    created_at=pkg.created_at,
                )
            )

        return package_reads

    async def get_package_details(
        self, user: User, package_id: uuid.UUID
    ) -> PackageDetailRead:
        query = (
            select(Package)
            .options(
                selectinload(Package.cooperative).selectinload(User.cooperative_profile),
                selectinload(Package.package_farmers).selectinload(PackageFarmer.farmer),
                selectinload(Package.investments).selectinload(Investment.investor),
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

        if user.role == UserRole.COOPERATIVE and package.cooperative_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view packages created by your cooperative.",
            )

        # 1. Financial & Settlement Calculations
        fund_amount = float(package.fund_amount or 0.0)
        expected_roi = float(package.expected_roi or 0.0)
        expected_settlement_amount = self._calculate_settlement(fund_amount, expected_roi)

        total_invested = sum(float(inv.amount or 0.0) for inv in package.investments)
        total_disbursed = sum(
            float(pf.allocated_amount or 0.0)
            for pf in package.package_farmers
            if pf.status == FarmerPackageStatus.DISBURSED
        )
        remaining_balance = total_invested - total_disbursed

        farmers_count = len(package.package_farmers)
        investors_count = len(package.investments)

        # 2. Role-based List Filtering & Detailed Mapping
        user_role_str = (
            user.role.value if hasattr(user.role, "value") else str(user.role)
        ).upper()

        if user_role_str == "INVESTOR" or user.role == UserRole.INVESTOR:
            assigned_farmers = []
            investors = []
        else:
            assigned_farmers = []
            for pf in package.package_farmers:
                farmer_obj = getattr(pf, "farmer", None)
                farmer_name = (
                    getattr(pf, "name", None)
                    or (
                        f"{getattr(farmer_obj, 'first_name', '')} {getattr(farmer_obj, 'last_name', '')}".strip()
                        if farmer_obj
                        else None
                    )
                    or getattr(farmer_obj, "full_name", "Farmer")
                )
                location = (
                    getattr(pf, "location", None)
                    or getattr(farmer_obj, "state", None)
                    or getattr(farmer_obj, "address", "N/A")
                )

                assigned_farmers.append(
                    PackageFarmerDetail(
                        id=pf.id,
                        package_id=pf.package_id,
                        farmer_id=pf.farmer_id,
                        name=farmer_name,
                        location=location,
                        allocated_amount=float(pf.allocated_amount or 0.0),
                        tenure_months=int(pf.tenure_months or package.tenure_months or 0),
                        expected_roi=float(pf.expected_roi or expected_roi),
                        photo=getattr(pf, "photo", getattr(farmer_obj, "photo", None)),
                        progress_stage=getattr(pf, "progress_stage", "Growing"),
                        progress_percentage=float(getattr(pf, "progress_percentage", 0.0)),
                        payout_date=getattr(pf, "payout_date", None),
                        payback_date=getattr(pf, "payback_date", package.expected_payback_date),
                        status=pf.status,
                    )
                )

            investors = []
            for inv in package.investments:
                inv_amount = float(inv.amount or 0.0)
                inv_settlement = self._calculate_settlement(inv_amount, expected_roi)
                inv_user = getattr(inv, "investor", None)
                inv_name = (
                    getattr(inv_user, "full_name", None)
                    or f"{getattr(inv_user, 'first_name', '')} {getattr(inv_user, 'last_name', '')}".strip()
                    or getattr(inv_user, "email", "Investor")
                ) if inv_user else "Investor"

                investors.append(
                    PackageInvestorDetail(
                        id=inv.id,
                        investor_id=inv.investor_id,
                        investor_name=inv_name,
                        amount=inv_amount,
                        expected_settlement=inv_settlement,
                        created_at=inv.created_at,
                        payback_due_date=getattr(inv, "payback_due_date", package.expected_payback_date),
                    )
                )

        coop_name = (
            package.cooperative.cooperative_profile.cooperative_name
            if package.cooperative and getattr(package.cooperative, "cooperative_profile", None)
            else getattr(package, "cooperative_name", None)
        )

        whats_included = self._parse_whats_included(getattr(package, "whats_included", None))

        return PackageDetailRead(
            id=package.id,
            cooperative_id=package.cooperative_id,
            cooperative_name=coop_name,
            title=package.title,
            package_type=package.package_type,
            category=package.category,
            farming_cycle=package.farming_cycle,
            short_description=package.short_description,
            fund_amount=fund_amount,
            tenure_months=package.tenure_months,
            expected_payback_date=package.expected_payback_date,
            expected_roi=expected_roi,
            cooperative_share=float(package.cooperative_share or 0.0),
            expected_settlement_amount=expected_settlement_amount,
            whats_included=whats_included,  # <-- Pass parsed items list
            farmers_count=farmers_count,
            investors_count=investors_count,
            status=package.status,
            financial_summary=PackageFinancialSummary(
                total_money_invested=total_invested,
                total_disbursed_to_farmers=total_disbursed,
                remaining_balance=remaining_balance,
            ),
            assigned_farmers=assigned_farmers,
            investors=investors,
        )

    async def get_package_investors(
        self, user: User, package_id: uuid.UUID
    ) -> List[PackageInvestorResponse]:
        user_role_str = (
            user.role.value if hasattr(user.role, "value") else str(user.role)
        ).upper()
        if user_role_str == "INVESTOR" or user.role == UserRole.INVESTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Investors cannot view investor details.",
            )

        pkg_res = await self.db.execute(select(Package).where(Package.id == package_id))
        package = pkg_res.scalars().first()

        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investment package not found.",
            )

        if user.role == UserRole.COOPERATIVE and package.cooperative_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view investors for your own packages.",
            )

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
                investor_name=f"{getattr(inv.investor, 'first_name', '') or ''} {getattr(inv.investor, 'last_name', '') or ''}".strip()
                or inv.investor.email,
                email=inv.investor.email,
                investor_type=getattr(inv.investor, "investor_type", None),
                amount=float(inv.amount),
                invested_at=inv.created_at,
                payback_due_date=getattr(inv, "payback_due_date", package.expected_payback_date)
                or package.expected_payback_date,
            )
            for inv in investments
        ]

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
            PackageType.STARTER: 100.00,
            PackageType.GROWTH: 300.00,
            PackageType.COMMERCIAL: 500.00,
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
