import math
import uuid
from typing import List, Optional, Union
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.farmer_model import Farm, Farmer, FarmingCategory, FarmStatus, Gender, WRSStatus
from app.models.cooperative_investment_model import Investment, InvestmentStatus
from app.models.package_model import PackageFarmer
from app.models.user_model import User, UserRole
from app.schemas.farmer_schema import (
    FarmCreate,
    FarmStatusUpdate,
    FarmerDirectoryItem,
    FarmerDirectoryMetrics,
    FarmerDirectoryResponse,
    PaginatedFarmerResponse,
)
from app.utils.cloudinary import upload_kyc_document


class FarmerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _has_active_investment(self, farmer_id: uuid.UUID) -> bool:
        """Helper to verify if a farmer is linked to any active investment."""
        stmt = (
            select(Investment.id)
            .join(PackageFarmer, Investment.package_id == PackageFarmer.package_id)
            .where(
                PackageFarmer.farmer_id == farmer_id,
                Investment.status == InvestmentStatus.ACTIVE,
            )
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def fetch_farmer_with_relations(self, farmer_id: uuid.UUID) -> Farmer:
        result = await self.db.execute(
            select(Farmer)
            .options(
                selectinload(Farmer.farms),
                selectinload(Farmer.cooperative).selectinload(
                    User.cooperative_profile
                ),
            )
            .where(Farmer.id == farmer_id)
        )
        farmer = result.scalars().first()
        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farmer profile with ID '{farmer_id}' not found.",
            )
        return farmer

    async def get_directory(
        self,
        cooperative_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        crop_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> FarmerDirectoryResponse:
        base_query = select(Farmer)

        if cooperative_id:
            base_query = base_query.where(
                Farmer.cooperative_id == cooperative_id
            )

        # --- 1. Top Bar Directory Metrics ---
        total_stmt = select(func.count()).select_from(base_query.subquery())
        verified_stmt = select(func.count()).select_from(
            base_query.where(Farmer.wrs_status ==
                             WRSStatus.VERIFIED).subquery()
        )
        pending_stmt = select(func.count()).select_from(
            base_query.where(Farmer.wrs_status ==
                             WRSStatus.NOT_VERIFIED).subquery()
        )

        total_farmers = (await self.db.execute(total_stmt)).scalar() or 0
        verified_farmers = (await self.db.execute(verified_stmt)).scalar() or 0
        pending_verification = (await self.db.execute(pending_stmt)).scalar() or 0

        metrics = FarmerDirectoryMetrics(
            total_farmers=total_farmers,
            verified_farmers=verified_farmers,
            pending_verification=pending_verification,
            removed_farmers=0,
        )

        # --- 2. Filter & Search Logic ---
        filtered_query = base_query.options(selectinload(Farmer.farms))

        if status_filter:
            norm_status = status_filter.strip().upper()
            if norm_status == "VERIFIED":
                filtered_query = filtered_query.where(
                    Farmer.wrs_status == WRSStatus.VERIFIED
                )
            elif norm_status in ["PENDING", "NOT_VERIFIED"]:
                filtered_query = filtered_query.where(
                    Farmer.wrs_status == WRSStatus.NOT_VERIFIED
                )

        has_crop_filter = crop_type and crop_type.lower() != "all"
        has_search_filter = bool(search and search.strip())

        # Safely join farms ONCE if crop or search filters are active
        if has_crop_filter or has_search_filter:
            filtered_query = filtered_query.outerjoin(Farmer.farms)

        if has_crop_filter:
            norm_crop = crop_type.strip().lower().replace(" ", "_")
            filtered_query = filtered_query.where(
                or_(
                    cast(Farmer.farming_category, String).ilike(
                        f"%{norm_crop}%"),
                    cast(Farm.farming_category, String).ilike(
                        f"%{norm_crop}%"),
                    Farm.name.ilike(f"%{crop_type}%"),
                )
            )

        if has_search_filter:
            pattern = f"%{search.strip()}%"
            filtered_query = filtered_query.where(
                or_(
                    Farmer.full_name.ilike(pattern),
                    Farmer.nin.ilike(pattern),
                    Farmer.phone_number.ilike(pattern),
                    cast(Farmer.farming_category, String).ilike(pattern),
                    cast(Farm.farming_category, String).ilike(pattern),
                    Farm.name.ilike(pattern),
                )
            )

        # Get total matching record count
        count_stmt = select(func.count()).select_from(
            filtered_query.distinct().subquery()
        )
        total_filtered = (await self.db.execute(count_stmt)).scalar() or 0

        # --- 3. Pagination ---
        offset = (page - 1) * page_size
        paginated_query = (
            filtered_query.distinct()
            .order_by(Farmer.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(paginated_query)
        farmers = result.scalars().unique().all()

        items = []
        for farmer in farmers:
            raw_cat = None
            if farmer.farming_category:
                raw_cat = farmer.farming_category
            elif farmer.farms and farmer.farms[0].farming_category:
                raw_cat = farmer.farms[0].farming_category

            category_val = "No Category"
            if raw_cat:
                str_cat = raw_cat.value if isinstance(
                    raw_cat, FarmingCategory) else str(raw_cat)
                category_val = str_cat.replace("_", " ").title()

            items.append(
                FarmerDirectoryItem(
                    id=farmer.id,
                    full_name=farmer.full_name,
                    photo=farmer.photo,
                    farming_category=category_val,
                    phone_number=farmer.phone_number,
                    date_added=farmer.date_added,
                    status="Verified"
                    if farmer.wrs_status == WRSStatus.VERIFIED
                    else "Pending",
                )
            )

        total_pages = (
            math.ceil(total_filtered / page_size) if page_size > 0 else 1
        )

        return FarmerDirectoryResponse(
            metrics=metrics,
            items=items,
            total=total_filtered,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def add_farmer(
        self,
        user: User,
        full_name: str,
        nin: str,
        phone_number: str,
        gender: Gender,
        farming_category: Optional[Union[FarmingCategory, str]] = None,
        photo: Optional[UploadFile] = None,
        additional_info: Optional[str] = None,
        wrs_status: WRSStatus = WRSStatus.NOT_VERIFIED,
        farms: Optional[List[FarmCreate]] = None,
    ) -> Farmer:
        if user.role != UserRole.COOPERATIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only cooperatives are permitted to register farmers.",
            )

        if not nin.isdigit() or len(nin) != 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIN must consist of exactly 11 numeric digits.",
            )

        if isinstance(farming_category, str):
            clean_cat = farming_category.strip().lower().replace(" ", "_")
            try:
                farming_category = FarmingCategory(clean_cat)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid farming category: '{farming_category}'",
                )

        photo_url = None
        if photo:
            photo_res = await upload_kyc_document(
                photo, "collabfarm/farmer_photos"
            )
            photo_url = photo_res.get("secure_url")

        # Extract enum string values safely
        cat_val = (
            farming_category.value
            if hasattr(farming_category, "value")
            else farming_category
        )
        gender_val = gender.value if hasattr(gender, "value") else gender
        wrs_val = wrs_status.value if hasattr(wrs_status, "value") else wrs_status

        farmer = Farmer(
            cooperative_id=user.id,
            full_name=full_name,
            nin=nin,
            phone_number=phone_number,
            gender=gender_val,
            farming_category=cat_val,
            photo=photo_url,
            additional_info=additional_info,
            wrs_status=wrs_val,
        )
        self.db.add(farmer)
        await self.db.flush()

        # Process attached farms only if provided
        if farms:
            for farm_item in farms:
                farm_cat_val = (
                    farm_item.farming_category.value
                    if hasattr(farm_item.farming_category, "value")
                    else farm_item.farming_category
                )
                farm_status_val = (
                    farm_item.status.value
                    if hasattr(farm_item.status, "value")
                    else farm_item.status
                )

                farm = Farm(
                    farmer_id=farmer.id,
                    name=farm_item.name,
                    location=farm_item.location,
                    size_in_hectares=farm_item.size_in_hectares,
                    farming_category=farm_cat_val,
                    status=farm_status_val,
                )
                self.db.add(farm)  # Must be indented inside the loop

        await self.db.commit()
        return await self.fetch_farmer_with_relations(farmer.id)
    
    
    async def list_farmers(
        self,
        search: Optional[str] = None,
        farming_category: Optional[Union[FarmingCategory, str]] = None,
        wrs_status: Optional[WRSStatus] = None,
        cooperative_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> PaginatedFarmerResponse:
        base_query = select(Farmer).options(
            selectinload(Farmer.farms),
            selectinload(Farmer.cooperative).selectinload(
                User.cooperative_profile
            ),
        )

        if cooperative_id:
            base_query = base_query.where(
                Farmer.cooperative_id == cooperative_id)
        if wrs_status:
            base_query = base_query.where(Farmer.wrs_status == wrs_status)

        has_cat_filter = bool(farming_category)
        has_search_filter = bool(search and search.strip())

        # Join farms once if filtering by category or searching
        if has_cat_filter or has_search_filter:
            base_query = base_query.outerjoin(Farmer.farms)

        if has_cat_filter:
            cat_str = (
                farming_category.value
                if isinstance(farming_category, FarmingCategory)
                else str(farming_category).strip().lower().replace(" ", "_")
            )
            base_query = base_query.where(
                or_(
                    cast(Farmer.farming_category, String).ilike(
                        f"%{cat_str}%"),
                    cast(Farm.farming_category, String).ilike(f"%{cat_str}%"),
                )
            )

        if has_search_filter:
            pattern = f"%{search.strip()}%"
            base_query = base_query.where(
                or_(
                    Farmer.full_name.ilike(pattern),
                    Farmer.phone_number.ilike(pattern),
                    Farmer.nin.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(
            base_query.distinct().subquery()
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        query = (
            base_query.distinct()
            .order_by(Farmer.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        farmers = result.scalars().unique().all()

        total_pages = math.ceil(total / page_size) if page_size > 0 else 1

        return PaginatedFarmerResponse(
            items=farmers,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_farmer_profile(self, farmer_id: uuid.UUID) -> Farmer:
        return await self.fetch_farmer_with_relations(farmer_id)

    async def update_farmer(
        self,
        farmer_id: uuid.UUID,
        user: User,
        full_name: Optional[str] = None,
        nin: Optional[str] = None,
        phone_number: Optional[str] = None,
        gender: Optional[Gender] = None,
        farming_category: Optional[Union[FarmingCategory, str]] = None,
        additional_info: Optional[str] = None,
        wrs_status: Optional[WRSStatus] = None,
        photo: Optional[UploadFile] = None,
    ) -> Farmer:
        farmer = await self.db.get(Farmer, farmer_id)

        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farmer profile with ID '{farmer_id}' not found.",
            )

        if user.role != UserRole.COOPERATIVE or farmer.cooperative_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are only authorized to modify farmers registered under your cooperative.",
            )

        if await self._has_active_investment(farmer_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot edit farmer profile while they have active investments.",
            )

        if nin is not None and (not nin.isdigit() or len(nin) != 11):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIN must consist of exactly 11 numeric digits.",
            )

        if isinstance(farming_category, str):
            clean_cat = farming_category.strip().lower().replace(" ", "_")
            try:
                farming_category = FarmingCategory(clean_cat)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid farming category: '{farming_category}'",
                )

        update_fields = {
            "full_name": full_name,
            "nin": nin,
            "phone_number": phone_number,
            "gender": gender,
            "farming_category": farming_category,
            "additional_info": additional_info,
            "wrs_status": wrs_status,
        }

        for key, value in update_fields.items():
            if value is not None:
                setattr(farmer, key, value)

        if photo:
            photo_res = await upload_kyc_document(
                photo, "collabfarm/farmer_photos"
            )
            farmer.photo = photo_res["secure_url"]

        await self.db.commit()
        return await self.fetch_farmer_with_relations(farmer.id)

    async def delete_farmer(self, farmer_id: uuid.UUID, user: User) -> None:
        farmer = await self.db.get(Farmer, farmer_id)

        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farmer profile with ID '{farmer_id}' not found.",
            )

        if user.role != UserRole.COOPERATIVE or farmer.cooperative_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are only authorized to delete farmers registered under your cooperative.",
            )

        if await self._has_active_investment(farmer_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete farmer profile while they have active investments.",
            )

        await self.db.delete(farmer)
        await self.db.commit()
        return None

    async def add_farm_to_farmer(
        self, cooperative_id: uuid.UUID, farmer_id: uuid.UUID, farm_data: FarmCreate
    ) -> Farm:
        stmt = select(Farmer).where(
            Farmer.id == farmer_id, Farmer.cooperative_id == cooperative_id
        )
        res = await self.db.execute(stmt)
        farmer = res.scalar_one_or_none()

        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farmer not found in this cooperative.",
            )

        cat_val = (
            farm_data.farming_category.value
            if hasattr(farm_data.farming_category, "value")
            else farm_data.farming_category
        )
        status_val = (
            farm_data.status.value
            if hasattr(farm_data.status, "value")
            else farm_data.status
        )

        new_farm = Farm(
            farmer_id=farmer_id,
            name=farm_data.name,
            location=farm_data.location,
            size_in_hectares=farm_data.size_in_hectares,
            farming_category=cat_val,
            status=status_val,
        )
        self.db.add(new_farm)
        await self.db.commit()
        await self.db.refresh(new_farm)
        return new_farm

    async def update_farm_status(
        self,
        cooperative_id: uuid.UUID,
        farm_id: uuid.UUID,
        status_update: FarmStatusUpdate,
    ) -> Farm:
        stmt = (
            select(Farm)
            .join(Farmer, Farm.farmer_id == Farmer.id)
            .where(Farm.id == farm_id, Farmer.cooperative_id == cooperative_id)
        )
        res = await self.db.execute(stmt)
        farm = res.scalar_one_or_none()

        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farm record not found.",
            )

        farm.status = status_update.status
        await self.db.commit()
        await self.db.refresh(farm)
        return farm

    async def get_farmer_farms(
        self,
        cooperative_id: uuid.UUID,
        farmer_id: uuid.UUID,
        active_only: bool = False,
    ) -> List[Farm]:
        stmt = (
            select(Farm)
            .join(Farmer, Farm.farmer_id == Farmer.id)
            .where(
                Farm.farmer_id == farmer_id,
                Farmer.cooperative_id == cooperative_id,
            )
        )

        if active_only:
            stmt = stmt.where(Farm.status == FarmStatus.ACTIVE)

        res = await self.db.execute(stmt)
        return list(res.scalars().all())
