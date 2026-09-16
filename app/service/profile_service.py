from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.profileModel import CooperativeProfile, GroupProfile, IndividualProfile
from app.models.userModel import InvestorType, User, UserRole, VerificationStatus
from app.utils.cloudinary import upload_kyc_document


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_individual_profile(
        self,
        user: User,
        full_name: str,
        email: str,
        phone_number: str,
        id_number: str,
        nationality: str,
        id_file: UploadFile,
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

        user.investor_type = InvestorType.INDIVIDUAL
        user.verification_status = VerificationStatus.APPROVED

        self.db.add(profile)
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
        email: str,
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
            email=email,
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
