import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.farmer_model import Gender, WRSStatus
from app.models.user_model import User
from app.schemas.farmer_schema import (
    FarmCreate,
    FarmRead,
    FarmerRead,
    FarmStatusUpdate,
    PaginatedFarmerResponse,
)
from app.services.farmer_service import FarmerService
from app.users import current_active_user

router = APIRouter(prefix="/farmers", tags=["Farmer Directory"])


@router.post("", response_model=FarmerRead, status_code=status.HTTP_201_CREATED)
async def add_farmer(
    full_name: str = Form(...),
    nin: str = Form(...),
    phone_number: str = Form(...),
    gender: Gender = Form(...),
    additional_info: Optional[str] = Form(None),
    wrs_status: WRSStatus = Form(WRSStatus.NOT_VERIFIED),
    photo: Optional[UploadFile] = File(None),
    farms_json: Optional[str] = Form(None),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    farms: Optional[List[FarmCreate]] = None
    if farms_json:
        try:
            raw_farms = json.loads(farms_json)
            farms = [FarmCreate(**f) for f in raw_farms]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON format for farms: {str(e)}",
            )

    return await FarmerService(db).add_farmer(
        user=user,
        full_name=full_name,
        nin=nin,
        phone_number=phone_number,
        gender=gender,
        photo=photo,
        additional_info=additional_info,
        wrs_status=wrs_status,
        farms=farms,
    )


@router.get("", response_model=PaginatedFarmerResponse)
async def list_farmers(
    search: Optional[str] = Query(None),
    farming_category: Optional[str] = Query(None),
    wrs_status: Optional[WRSStatus] = Query(None),
    cooperative_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).list_farmers(
        search=search,
        farming_category=farming_category,
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
    phone_number: Optional[str] = Form(None),
    gender: Optional[Gender] = Form(None),
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
        phone_number=phone_number,
        gender=gender,
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


@router.post(
    "/{farmer_id}/farms", response_model=FarmRead, status_code=status.HTTP_201_CREATED
)
async def add_farm_to_farmer(
    farmer_id: uuid.UUID,
    farm_data: FarmCreate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).add_farm_to_farmer(
        cooperative_id=user.id, farmer_id=farmer_id, farm_data=farm_data
    )


@router.patch("/farms/{farm_id}/status", response_model=FarmRead)
async def update_farm_status(
    farm_id: uuid.UUID,
    status_update: FarmStatusUpdate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).update_farm_status(
        cooperative_id=user.id, farm_id=farm_id, status_update=status_update
    )


@router.get("/{farmer_id}/farms", response_model=List[FarmRead])
async def get_farmer_farms(
    farmer_id: uuid.UUID,
    active_only: bool = Query(False),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await FarmerService(db).get_farmer_farms(
        cooperative_id=user.id, farmer_id=farmer_id, active_only=active_only
    )