import math
import uuid
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.farmer_model import Farmer, Gender, WRSStatus
from app.models.user_model import User, UserRole
from app.schemas.farmer_schema import PaginatedFarmerResponse
from app.utils.cloudinary import upload_kyc_document


class FarmerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def fetch_farmer_with_relations(self, farmer_id: uuid.UUID) -> Farmer:
        result = await self.db.execute(
            select(Farmer)
            .options(
                selectinload(Farmer.cooperative).selectinload(
                    User.cooperative_profile
                )
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
        crop_type: str,
        phone_number: str,
        gender: Gender,
        farm_size_acres: float,
        farm_address: str,
        photo: UploadFile,
        additional_info: Optional[str] = None,
        wrs_status: WRSStatus = WRSStatus.NOT_VERIFIED,
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

        photo_res = await upload_kyc_document(photo, "collabfarm/farmer_photos")

        farmer = Farmer(
            cooperative_id=user.id,
            full_name=full_name,
            nin=nin,
            crop_type=crop_type,
            phone_number=phone_number,
            gender=gender,
            farm_size_acres=farm_size_acres,
            farm_address=farm_address,
            photo=photo_res["secure_url"],
            additional_info=additional_info,
            wrs_status=wrs_status,
        )

        self.db.add(farmer)
        await self.db.commit()

        return await self.fetch_farmer_with_relations(farmer.id)

    async def list_farmers(
        self,
        search: Optional[str] = None,
        crop_type: Optional[str] = None,
        wrs_status: Optional[WRSStatus] = None,
        cooperative_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 12,
    ) -> PaginatedFarmerResponse:
        query = select(Farmer).options(
            selectinload(Farmer.cooperative).selectinload(User.cooperative_profile)
        )

        if search:
            query = query.where(
                Farmer.full_name.ilike(f"%{search}%")
                | Farmer.nin.ilike(f"%{search}%")
                | Farmer.crop_type.ilike(f"%{search}%")
            )

        if crop_type:
            query = query.where(Farmer.crop_type.ilike(f"%{crop_type}%"))

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
        crop_type: Optional[str] = None,
        phone_number: Optional[str] = None,
        gender: Optional[Gender] = None,
        farm_size_acres: Optional[float] = None,
        farm_address: Optional[str] = None,
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

        if nin is not None and (not nin.isdigit() or len(nin) != 11):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIN must consist of exactly 11 numeric digits.",
            )

        update_fields = {
            "full_name": full_name,
            "nin": nin,
            "crop_type": crop_type,
            "phone_number": phone_number,
            "gender": gender,
            "farm_size_acres": farm_size_acres,
            "farm_address": farm_address,
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

        await self.db.delete(farmer)
        await self.db.commit()
        return None