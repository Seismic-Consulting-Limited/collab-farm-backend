# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.router.common import ErrorCode
from pydantic import BaseModel, EmailStr
from app.schemas import UserRead, UserCreate, UserUpdate
from fastapi_users.exceptions import UserAlreadyExists

from app.users import get_user_manager, auth_backend

router = APIRouter(prefix="/auth", tags=["auth"])


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @property
    def username(self) -> str:
        return self.email


@router.post("/login")
async def login(
    credentials: UserLogin,
    user_manager=Depends(get_user_manager),
    strategy=Depends(auth_backend.get_strategy),
):
    user = await user_manager.authenticate(credentials)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
        )

    token = await strategy.write_token(user)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    user_manager=Depends(get_user_manager),
):
    try:
        return await user_manager.create(user_create)
    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.REGISTER_USER_ALREADY_EXISTS,
        )
