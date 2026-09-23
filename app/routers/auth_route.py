from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.schemas.user_schema import (
    ForgotPasswordSchema,
    ResetPasswordSchema,
    UserCreate,
    VerifyOTPSchema,
)
from app.services.auth_service import AuthService
from app.users import UserManager, auth_backend, get_user_manager

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_manager: UserManager = Depends(get_user_manager),
    strategy=Depends(auth_backend.get_strategy),
):
    return await AuthService(user_manager=user_manager, strategy=strategy).login(
        request, form_data
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    background_tasks: BackgroundTasks,
    user_manager: UserManager = Depends(get_user_manager),
    strategy=Depends(auth_backend.get_strategy),
):
    return await AuthService(
        user_manager=user_manager, strategy=strategy
    ).register(user_create, background_tasks)


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(
    payload: VerifyOTPSchema,
    user_manager: UserManager = Depends(get_user_manager),
):
    return await AuthService(user_manager=user_manager).verify_email_otp(
        payload
    )


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    email: EmailStr,
    background_tasks: BackgroundTasks,
    user_manager: UserManager = Depends(get_user_manager),
):
    return await AuthService(
        user_manager=user_manager
    ).resend_verification_email(email, background_tasks)


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordSchema,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
):
    return await AuthService(session=session).forgot_password(
        payload, background_tasks
    )


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordSchema,
    user_manager: UserManager = Depends(get_user_manager),
):
    return await AuthService(user_manager=user_manager).reset_password(payload)
