import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.farmer_model import Gender, WRSStatus
from app.models.user_model import User
from app.schemas.farmer_schema import FarmerRead, PaginatedFarmerResponse
from app.services.farmer_service import FarmerService
from app.users import current_active_user

router = APIRouter(prefix="/farmers", tags=["Farmer Directory"])


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
    return await FarmerService(db).add_farmer(
        user=user,
        full_name=full_name,
        nin=nin,
        crop_type=crop_type,
        phone_number=phone_number,
        gender=gender,
        farm_size_acres=farm_size_acres,
        farm_address=farm_address,
        photo=photo,
        additional_info=additional_info,
        wrs_status=wrs_status,
    )


@router.get("", response_model=PaginatedFarmerResponse)
async def list_farmers(
    search: Optional[str] = Query(
        None, description="Search by name, NIN, or crop type"
    ),
    crop_type: Optional[str] = Query(None),
    wrs_status: Optional[WRSStatus] = Query(None),
    cooperative_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).list_farmers(
        search=search,
        crop_type=crop_type,
        wrs_status=wrs_status,
        cooperative_id=cooperative_id,
        page=page,
        page_size=page_size,
    )


@router.get("/{farmer_id}", response_model=FarmerRead)
async def get_farmer_profile(
    farmer_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).get_farmer_profile(farmer_id)


@router.patch("/{farmer_id}", response_model=FarmerRead)
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
    return await FarmerService(db).update_farmer(
        farmer_id=farmer_id,
        user=user,
        full_name=full_name,
        nin=nin,
        crop_type=crop_type,
        phone_number=phone_number,
        gender=gender,
        farm_size_acres=farm_size_acres,
        farm_address=farm_address,
        additional_info=additional_info,
        wrs_status=wrs_status,
        photo=photo,
    )


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farmer(
    farmer_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).delete_farmer(farmer_id=farmer_id, user=user)