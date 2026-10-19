from typing import List
from fastapi import Depends, HTTPException, status
from app.models.user_model import User, UserRole
from app.users import current_active_user  

def require_roles(allowed_roles: List[UserRole]):
    async def role_checker(user: User = Depends(current_active_user)) -> User:
        user_role_str = (
            user.role.value if hasattr(user.role, "value") else str(user.role)
        ).upper()

        allowed_role_strs = [
            r.value.upper() if hasattr(r, "value") else str(r).upper()
            for r in allowed_roles
        ]

        if user_role_str not in allowed_role_strs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Your account is not authorized for this portal.",
            )
        return user

    return role_checker