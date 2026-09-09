from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models.profileModel import CooperativeProfile, GroupProfile, IndividualProfile
from app.models.userModel import InvestorType, User, UserRole, VerificationStatus
from app.users import current_active_user
# Adjusted to your utility path
from app.utils.cloudinary import upload_kyc_document

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
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts bypass profile verification.",
        )

    if user.role != UserRole.INVESTOR or user.investor_type != InvestorType.INDIVIDUAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account type mismatch. You are not registered as an Individual Investor.",
        )

    id_file_res = await upload_kyc_document(id_file, "collabfarm/individual_ids")

    profile = IndividualProfile(
        user_id=user.id,
        full_name=full_name,
        email=email,
        phone_number=phone_number,
        id_number=id_number,
        nationality=nationality,
        id_file=id_file_res["secure_url"],
    )

    user.verification_status = VerificationStatus.APPROVED

    db.add(profile)
    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "message": "Individual Investor profile submitted and account verified successfully.",
        "verification_status": user.verification_status,
    }


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
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts bypass profile verification.",
        )

    if user.role != UserRole.INVESTOR or user.investor_type != InvestorType.INVESTMENT_GROUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account type mismatch. You are not registered as an Investment Group.",
        )

    reg_file_res = await upload_kyc_document(company_registration_file, "collabfarm/group_registrations")
    proof_file_res = await upload_kyc_document(proof_of_address_file, "collabfarm/group_proofs")

    profile = GroupProfile(
        user_id=user.id,
        company_name=company_name,
        company_address=company_address,
        email=email,
        phone_number=phone_number,
        year_established=year_established,
        company_registration_number=company_registration_number,
        company_registration_file=reg_file_res["secure_url"],
        proof_of_address_file=proof_file_res["secure_url"],
    )

    user.verification_status = VerificationStatus.APPROVED

    db.add(profile)
    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "message": "Group Investment profile submitted and account verified successfully.",
        "verification_status": user.verification_status,
    }


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
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts bypass profile verification.",
        )

    if user.role != UserRole.COOPERATIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account type mismatch. You are not registered as a Cooperative.",
        )

    cert_file_res = await upload_kyc_document(registration_certificate_file, "collabfarm/cooperative_certs")
    proof_file_res = await upload_kyc_document(proof_of_address_file, "collabfarm/cooperative_proofs")

    profile = CooperativeProfile(
        user_id=user.id,
        cooperative_name=cooperative_name,
        year_established=year_established,
        registration_number=registration_number,
        email=email,
        address=address,
        lga=lga,
        state=state,
        registration_certificate_file=cert_file_res["secure_url"],
        proof_of_address_file=proof_file_res["secure_url"],
    )

    user.verification_status = VerificationStatus.APPROVED

    db.add(profile)
    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "message": "Cooperative profile submitted and account verified successfully.",
        "verification_status": user.verification_status,
    }
