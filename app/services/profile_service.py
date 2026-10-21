from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.profile_model import CooperativeProfile, GroupProfile, IndividualProfile
from app.schemas.profile_schema import UserProfile, IndividualProfileRead, CooperativeProfileRead, GroupProfileRead
from app.models.user_model import InvestorType, User, UserRole, VerificationStatus
from app.utils.cloudinary import upload_kyc_document
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid
from typing import Optional

class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_individual_profile(
        self,
        user: User,
        id_number: str,
        nationality: str,
        id_file: UploadFile,
        address: Optional[str] = None,
    ) -> dict:
        if user.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin accounts bypass profile verification.",
            )

        if user.role != UserRole.INVESTOR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account type mismatch. You are not registered as an Investor.",
            )

        # 1. Upload KYC Document
        id_file_res = await upload_kyc_document(id_file, "collabfarm/individual_ids")

        # 2. Check for existing profile (Upsert handling)
        stmt = select(IndividualProfile).where(IndividualProfile.user_id == user.id)
        res = await self.db.execute(stmt)
        profile = res.unique().scalar_one_or_none()

        if not profile:
            profile = IndividualProfile(
                user_id=user.id,
                id_number=id_number,
                nationality=nationality,
                address=address,
                id_file=id_file_res["secure_url"],
            )
            self.db.add(profile)
        else:
            profile.id_number = id_number
            profile.nationality = nationality
            profile.address = address
            profile.id_file = id_file_res["secure_url"]

        # 3. Update User Verification Attributes
        user.investor_type = InvestorType.INDIVIDUAL
        user.verification_status = VerificationStatus.APPROVED

        await self.db.commit()
        await self.db.refresh(user)

        return {
            "status": "success",
            "message": "Individual Investor profile submitted and account verified successfully.",
            "verification_status": user.verification_status,
        }

    async def submit_group_profile(
        self,
        user: User,
        company_name: str,
        company_address: str,
        email: str,
        phone_number: str,
        year_established: int,
        company_registration_number: str,
        company_registration_file: UploadFile,
        proof_of_address_file: UploadFile,
    ) -> dict:
        if user.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin accounts bypass profile verification.",
            )

        if user.role != UserRole.INVESTOR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account type mismatch. You are not registered as an Investor.",
            )

        reg_file_res = await upload_kyc_document(
            company_registration_file, "collabfarm/group_registrations"
        )
        proof_file_res = await upload_kyc_document(
            proof_of_address_file, "collabfarm/group_proofs"
        )

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

        user.investor_type = InvestorType.INVESTMENT_GROUP
        user.verification_status = VerificationStatus.APPROVED

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(user)

        return {
            "status": "success",
            "message": "Group Investment profile submitted and account verified successfully.",
            "verification_status": user.verification_status,
        }

    async def submit_cooperative_profile(
        self,
        user: User,
        cooperative_name: str,
        year_established: int,
        registration_number: str,
        phone_number: str,
        address: str,
        lga: str,
        state: str,
        registration_certificate_file: UploadFile,
        proof_of_address_file: UploadFile,
    ) -> dict:
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

        cert_file_res = await upload_kyc_document(
            registration_certificate_file, "collabfarm/cooperative_certs"
        )
        proof_file_res = await upload_kyc_document(
            proof_of_address_file, "collabfarm/cooperative_proofs"
        )

        profile = CooperativeProfile(
            user_id=user.id,
            cooperative_name=cooperative_name,
            year_established=year_established,
            registration_number=registration_number,
            phone_number=phone_number,
            address=address,
            lga=lga,
            state=state,
            registration_certificate_file=cert_file_res["secure_url"],
            proof_of_address_file=proof_file_res["secure_url"],
        )

        user.verification_status = VerificationStatus.APPROVED

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(user)

        return {
            "status": "success",
            "message": "Cooperative profile submitted and account verified successfully.",
            "verification_status": user.verification_status,
        }
    
    async def get_user_profile(self, user_id: uuid.UUID) -> UserProfile:
        query = (
            select(User)
            .options(
                selectinload(User.individual_profile),
                selectinload(User.group_profile),
                selectinload(User.cooperative_profile),
            )
            .where(User.id == user_id)
        )
        result = await self.db.execute(query)
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found.",
            )

        active_profile = None

        if user.individual_profile:
            ip = user.individual_profile
            
            # Instantiate schema with first_name and last_name directly from user
            active_profile = IndividualProfileRead(
                id=ip.id,
                user_id=ip.user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone_number=user.phone_number,
                id_number=ip.id_number,
                id_file=ip.id_file,
                nationality=ip.nationality,
                address=ip.address,
                created_at=ip.created_at,
                updated_at=ip.updated_at,
            )
        elif user.group_profile:
            active_profile = GroupProfileRead.model_validate(user.group_profile)
        elif user.cooperative_profile:
            active_profile = CooperativeProfileRead.model_validate(user.cooperative_profile)

        return UserProfile(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            role=user.role,
            investor_type=user.investor_type,
            verification_status=user.verification_status,
            profile=active_profile,
        )