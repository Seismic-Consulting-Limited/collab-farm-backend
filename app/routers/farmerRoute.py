import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_async_session
from app.models.farmerModel import Farmer, Gender, WRSStatus
from app.models.userModel import User, UserRole
from app.schemas.farmerSchema import FarmerRead, PaginatedFarmerResponse
from app.users import current_active_user
from app.utils.cloudinary import upload_kyc_document

router = APIRouter(prefix="/farmers", tags=["Farmer Directory"])


async def fetch_farmer_with_relations(db: AsyncSession, farmer_id: uuid.UUID) -> Farmer:
    """Helper to fetch a farmer with eager-loaded cooperative user and profile details."""
    result = await db.execute(
        select(Farmer)
        .options(
            selectinload(Farmer.cooperative).selectinload(
                User.cooperative_profile)
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


@router.post("", response_model=FarmerRead, status_code=status.HTTP_201_CREATED)
async def add_farmer(
    full_name: str = Form(...),
    nin: str = Form(...),
    crop_type: str = Form(...),
    phone_number: str = Form(...),
    gender: Gender = Form(...),
    farm_size_acres: float = Form(...),
    farm_address: str = Form(...),
    additional_info: Optional[str] = Form(None),
    wrs_status: WRSStatus = Form(WRSStatus.NOT_VERIFIED),
    photo: UploadFile = File(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
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

    db.add(farmer)
    await db.commit()

    return await fetch_farmer_with_relations(db, farmer.id)


@router.get("", response_model=PaginatedFarmerResponse)
async def list_farmers(
    search: Optional[str] = Query(
        None, description="Search by name, NIN, or crop type"),
    crop_type: Optional[str] = Query(None),
    wrs_status: Optional[WRSStatus] = Query(None),
    cooperative_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
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
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    farmers = result.scalars().all()

    return PaginatedFarmerResponse(
        items=farmers,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{farmer_id}", response_model=FarmerRead)
async def get_farmer_profile(
    farmer_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await fetch_farmer_with_relations(db, farmer_id)


@router.put("/{farmer_id}", response_model=FarmerRead)
async def update_farmer(
    farmer_id: uuid.UUID,
    full_name: Optional[str] = Form(None),
    nin: Optional[str] = Form(None),
    crop_type: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    gender: Optional[Gender] = Form(None),
    farm_size_acres: Optional[float] = Form(None),
    farm_address: Optional[str] = Form(None),
    additional_info: Optional[str] = Form(None),
    wrs_status: Optional[WRSStatus] = Form(None),
    photo: Optional[UploadFile] = File(None),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    farmer = await db.get(Farmer, farmer_id)

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

    await db.commit()

    return await fetch_farmer_with_relations(db, farmer.id)


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farmer(
    farmer_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    farmer = await db.get(Farmer, farmer_id)

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

    await db.delete(farmer)
    await db.commit()
    return None
