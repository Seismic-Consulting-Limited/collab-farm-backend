import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, InvestorType, VerificationStatus
from app.models.profile import IndividualProfile, GroupProfile
from app.users import current_unsubmitted_user
from app.db import get_async_session

router = APIRouter(tags=["Investor Update Profile"])


@router.post("/individual-investor", status_code=status.HTTP_201_CREATED)
async def submit_individual_investor(
    full_name: str = Form(...),
    phone_number: str = Form(...),
    dob: str = Form(...),
    nationality: str = Form(...),
    residential_address: str = Form(...),
    id_type: str = Form(...),
    id_number: str = Form(...),
    investment_preferences: str = Form(...),
    id_doc_file: UploadFile = File(...),
    user: User = Depends(current_unsubmitted_user),
    db: AsyncSession = Depends(get_async_session)
):
    if user.investor_type != InvestorType.INDIVIDUAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account type mismatch. You are not registered as an individual investor."
        )

    try:
        preferences_dict = json.loads(investment_preferences)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid JSON in investment_preferences")

    id_doc_bytes = await id_doc_file.read()

    new_profile = IndividualProfile(
        user_id=user.id,
        full_name=full_name,
        phone_number=phone_number,
        dob=dob,
        nationality=nationality,
        residential_address=residential_address,
        id_type=id_type,
        id_number=id_number,
        id_doc_file=id_doc_bytes,
        id_doc_filename=id_doc_file.filename,
        investment_preferences=preferences_dict
    )

    # This is where i approved the investor details
    user.investor_type = InvestorType.INDIVIDUAL
    user.verification_status = VerificationStatus.APPROVED

    db.add(new_profile)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "Individual KYC submitted successfully. Your account is pending admin review.",
        "verification_status": user.verification_status.value
    }


@router.post("/investment-group", status_code=status.HTTP_201_CREATED)
async def submit_group_investor(
    cooperative_name: str = Form(...),
    cooperative_type: str = Form(...),
    registration_number: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    address: str = Form(...),
    year_established: int = Form(...),
    rep_name: str = Form(...),
    rep_contact: str = Form(...),
    tax_id: str = Form(...),
    senior_mgmt_list: str = Form(...),
    investment_preferences: str = Form(...),
    cac_cert_file: UploadFile = File(...),
    rep_id_file: UploadFile = File(...),
    user: User = Depends(current_unsubmitted_user),
    db: AsyncSession = Depends(get_async_session)
):
    if user.investor_type != InvestorType.INVESTMENT_GROUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account type mismatch. You are not registered as an investment group."
        )

    try:
        preferences_dict = json.loads(investment_preferences)
        mgmt_list_dict = json.loads(senior_mgmt_list)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid JSON in nested text fields")

    cac_cert_bytes = await cac_cert_file.read()
    rep_id_bytes = await rep_id_file.read()

    new_profile = GroupProfile(
        user_id=user.id,
        cooperative_name=cooperative_name,
        cooperative_type=cooperative_type,
        registration_number=registration_number,
        email=email,
        phone_number=phone_number,
        address=address,
        year_established=year_established,
        rep_name=rep_name,
        rep_contact=rep_contact,
        senior_mgmt_list=mgmt_list_dict,
        tax_id=tax_id,
        cac_cert_file=cac_cert_bytes,
        cac_cert_filename=cac_cert_file.filename,
        rep_id_file=rep_id_bytes,
        rep_id_filename=rep_id_file.filename,
        investment_preferences=preferences_dict
    )

    # This is where i approved the investor details
    user.investor_type = InvestorType.INVESTMENT_GROUP
    user.verification_status = VerificationStatus.APPROVED

    db.add(new_profile)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "Investment Group KYC submitted successfully. Your account is pending admin review.",
        "verification_status": user.verification_status.value
    }
