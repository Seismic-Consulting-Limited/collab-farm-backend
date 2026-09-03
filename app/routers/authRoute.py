from pydantic import BaseModel, EmailStr, ValidationError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi_users.router.common import ErrorCode
from pydantic import BaseModel, EmailStr
from app.schemas.userSchema import UserRead, UserCreate, ForgotPasswordSchema, ResetPasswordSchema
from fastapi_users.exceptions import UserAlreadyExists, UserNotExists
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.password import PasswordHelper
from sqlalchemy.future import select
from app.utils.emails import send_reset_email_background
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session
from app.users import get_user_manager, auth_backend, UserManager
from app.models.userModel import User
from app.utils.security import generate_reset_token, verify_reset_token

router = APIRouter(prefix="/auth", tags=["Auth"])

password_helper = PasswordHelper()


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @property
    def username(self) -> str:
        return self.email


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_manager=Depends(get_user_manager),
    strategy=Depends(auth_backend.get_strategy),
):
    content_type = request.headers.get("content-type", "")

    try:
        if "application/json" in content_type:
            body = await request.json()
            credentials = UserLogin(**body)
        else:
            credentials = UserLogin(
                email=form_data.username,
                password=form_data.password,
            )
    except (ValidationError, Exception):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email or password format.",
        )

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


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordSchema,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalars().first()

    if user:
        token = generate_reset_token(user.email)
        send_reset_email_background(user.email, token, background_tasks)

    return {
        "status": "success",
        "message": "If an account with that email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordSchema,
    user_manager: UserManager = Depends(get_user_manager)
):

    email = verify_reset_token(payload.token, max_age=3600)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset link is invalid or has expired."
        )

    try:
        user = await user_manager.get_by_email(email)
    except UserNotExists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account associated with this token was not found."
        )

    hashed_password = user_manager.password_helper.hash(payload.new_password)
    await user_manager.user_db.update(user, {"hashed_password": hashed_password})

    return {
        "status": "success",
        "message": "Your password has been successfully reset. You can now log in."
    }
