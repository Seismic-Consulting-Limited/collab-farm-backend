from fastapi import Depends, HTTPException, status
from app.models.user_model import User, UserRole, VerificationStatus
from app.users import current_active_user


async def require_approved_investor(
    user: User = Depends(current_active_user),
) -> User:
    if user.role == UserRole.INVESTOR and user.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PROFILE_VERIFICATION_REQUIRED",
                "message": "Your profile must be submitted and approved before accessing this resource.",
                "verification_status": user.verification_status,
            },
        )
    return user