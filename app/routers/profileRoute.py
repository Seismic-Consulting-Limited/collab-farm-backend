from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session
from app.models.userModel import User
from app.service.profile_service import ProfileService
from app.users import current_active_user, get_user_manager, UserManager
from app.service.auth_service import AuthService
from app.schemas.userSchema import ChangePassword

router = APIRouter(prefix="/profile", tags=["Profile Management"])


@router.post("/individual-investor", status_code=status.HTTP_201_CREATED)
async def submit_individual_profile(
    full_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    id_number: str = Form(...),
    nationality: str = Form(...),
    id_file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProfileService(db).submit_individual_profile(
        user=user,
        full_name=full_name,
        email=email,
        phone_number=phone_number,
        id_number=id_number,
        nationality=nationality,
        id_file=id_file,
    )


@router.post("/investment-group", status_code=status.HTTP_201_CREATED)
async def submit_group_profile(
    company_name: str = Form(...),
    company_address: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    year_established: int = Form(...),
    company_registration_number: str = Form(...),
    company_registration_file: UploadFile = File(...),
    proof_of_address_file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProfileService(db).submit_group_profile(
        user=user,
        company_name=company_name,
        company_address=company_address,
        email=email,
        phone_number=phone_number,
        year_established=year_established,
        company_registration_number=company_registration_number,
        company_registration_file=company_registration_file,
        proof_of_address_file=proof_of_address_file,
    )


@router.post("/cooperative", status_code=status.HTTP_201_CREATED)
async def submit_cooperative_profile(
    cooperative_name: str = Form(...),
    year_established: int = Form(...),
    registration_number: str = Form(...),
    email: str = Form(...),
    address: str = Form(...),
    lga: str = Form(...),
    state: str = Form(...),
    registration_certificate_file: UploadFile = File(...),
    proof_of_address_file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await ProfileService(db).submit_cooperative_profile(
        user=user,
        cooperative_name=cooperative_name,
        year_established=year_established,
        registration_number=registration_number,
        email=email,
        address=address,
        lga=lga,
        state=state,
        registration_certificate_file=registration_certificate_file,
        proof_of_address_file=proof_of_address_file,
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: ChangePassword,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    return await AuthService(user_manager=user_manager).change_password(
        user=user, payload=payload
    )
