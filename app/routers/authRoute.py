from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.schemas.userSchema import (
    ForgotPasswordSchema,
    ResetPasswordSchema,
    UserCreate,
    UserRead,
)
from app.service.auth_service import AuthService
from app.users import UserManager, auth_backend, get_user_manager

router = APIRouter(prefix="/auth", tags=["Auth"])


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


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    user_manager: UserManager = Depends(get_user_manager),
):
    return await AuthService(user_manager=user_manager).register(user_create)


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