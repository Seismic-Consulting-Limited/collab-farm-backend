import math
import uuid
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.farmer_model import Farm, Farmer, FarmStatus, Gender, WRSStatus
from app.models.investment_model import Investment, InvestmentStatus
from app.models.package_model import PackageFarmer
from app.models.user_model import User, UserRole
from app.schemas.farmer_schema import FarmCreate, FarmStatusUpdate, PaginatedFarmerResponse
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

    async def add_farmer(
        self,
        user: User,
        full_name: str,
        nin: str,
        phone_number: str,
        gender: Gender,
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

        photo_url = None
        if photo:
            photo_res = await upload_kyc_document(photo, "collabfarm/farmer_photos")
            photo_url = photo_res.get("secure_url")

        farmer = Farmer(
            cooperative_id=user.id,
            full_name=full_name,
            nin=nin,
            phone_number=phone_number,
            gender=gender,
            photo=photo_url,
            additional_info=additional_info,
            wrs_status=wrs_status,
        )
        self.db.add(farmer)
        await self.db.flush()

        if farms:
            for farm_item in farms:
                farm = Farm(
                    farmer_id=farmer.id,
                    name=farm_item.name,
                    location=farm_item.location,
                    size_in_hectares=farm_item.size_in_hectares,
                    farming_category=farm_item.farming_category,
                    status=farm_item.status,
                )
                self.db.add(farm)

        await self.db.commit()
        return await self.fetch_farmer_with_relations(farmer.id)

    async def list_farmers(
        self,
        search: Optional[str] = None,
        farming_category: Optional[str] = None,
        wrs_status: Optional[WRSStatus] = None,
        cooperative_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> PaginatedFarmerResponse:
        query = (
            select(Farmer)
            .outerjoin(Farmer.farms)
            .options(
                selectinload(Farmer.farms),
                selectinload(Farmer.cooperative).selectinload(
                    User.cooperative_profile),
            )
            .distinct()
        )

        if search:
            query = query.where(
                Farmer.full_name.ilike(f"%{search}%")
                | Farmer.nin.ilike(f"%{search}%")
                | Farm.name.ilike(f"%{search}%")
                | Farm.farming_category.ilike(f"%{search}%")
                | Farm.location.ilike(f"%{search}%")
            )

        if farming_category:
            query = query.where(
                Farm.farming_category.ilike(f"%{farming_category}%"))

        if wrs_status:
            query = query.where(Farmer.wrs_status == wrs_status)

        if cooperative_id:
            query = query.where(Farmer.cooperative_id == cooperative_id)

        query = query.order_by(Farmer.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        farmers = result.scalars().all()

        return PaginatedFarmerResponse(
            items=farmers,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total > 0 else 1,
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

        update_fields = {
            "full_name": full_name,
            "nin": nin,
            "phone_number": phone_number,
            "gender": gender,
            "additional_info": additional_info,
            "wrs_status": wrs_status,
        }

        for key, value in update_fields.items():
            if value is not None:
                setattr(farmer, key, value)

        if photo:
            photo_res = await upload_kyc_document(photo, "collabfarm/farmer_photos")
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

        new_farm = Farm(
            farmer_id=farmer_id,
            name=farm_data.name,
            location=farm_data.location,
            size_in_hectares=farm_data.size_in_hectares,
            farming_category=farm_data.farming_category,
            status=farm_data.status,
        )
        self.db.add(new_farm)
        await self.db.commit()
        await self.db.refresh(new_farm)
        return new_farm

    async def update_farm_status(
        self, cooperative_id: uuid.UUID, farm_id: uuid.UUID, status_update: FarmStatusUpdate
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
        self, cooperative_id: uuid.UUID, farmer_id: uuid.UUID, active_only: bool = False
    ) -> List[Farm]:
        stmt = (
            select(Farm)
            .join(Farmer, Farm.farmer_id == Farmer.id)
            .where(Farm.farmer_id == farmer_id, Farmer.cooperative_id == cooperative_id)
        )

        if active_only:
            stmt = stmt.where(Farm.status == FarmStatus.ACTIVE)

        res = await self.db.execute(stmt)
        return list(res.scalars().all())
