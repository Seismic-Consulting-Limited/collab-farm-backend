from fastapi import BackgroundTasks, HTTPException, Request, status
from fastapi_users.exceptions import UserAlreadyExists, UserNotExists
from fastapi_users.router.common import ErrorCode
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user_model import User
from app.schemas.user_schema import (
    ChangePassword,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    UserCreate,
)
from app.utils.emails import (
    send_reset_email_background,
    send_verification_email_background,
)
from app.utils.security import (
    create_email_verification_token,
    decode_email_verification_token,
    generate_reset_token,
    verify_reset_token,
)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @property
    def username(self) -> str:
        return self.email


class AuthService:
    def __init__(
        self,
        user_manager=None,
        session: AsyncSession | None = None,
        strategy=None,
    ):
        self.user_manager = user_manager
        self.session = session
        self.strategy = strategy

    async def login(self, request: Request, form_data) -> dict:
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

        user = await self.user_manager.authenticate(credentials)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            )

        token = await self.strategy.write_token(user)
        return {"access_token": token, "token_type": "bearer"}

    async def register(self, user_create: UserCreate, background_tasks: BackgroundTasks):
        try:
            user = await self.user_manager.create(user_create)

            # Generate token and send verification email in background
            token = create_email_verification_token(user.email)
            send_verification_email_background(
                user.email, token, background_tasks)

            return user
        except UserAlreadyExists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.REGISTER_USER_ALREADY_EXISTS,
            )

    async def verify_email(self, token: str) -> dict:
        email = decode_email_verification_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token.",
            )

        try:
            user = await self.user_manager.get_by_email(email)
        except UserNotExists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account associated with this token was not found.",
            )

        if user.is_verified:
            return {
                "status": "success",
                "message": "Account is already verified.",
            }

        await self.user_manager.user_db.update(user, {"is_verified": True})

        return {
            "status": "success",
            "message": "Email verified successfully. You can now log in.",
        }

    async def resend_verification_email(
        self, email: str, background_tasks: BackgroundTasks
    ) -> dict:
        try:
            user = await self.user_manager.get_by_email(email)
        except UserNotExists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found.",
            )

        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is already verified.",
            )

        token = create_email_verification_token(user.email)
        send_verification_email_background(user.email, token, background_tasks)

        return {
            "status": "success",
            "message": "Verification email has been sent successfully.",
        }

    async def forgot_password(
        self, payload: ForgotPasswordSchema, background_tasks: BackgroundTasks
    ) -> dict:
        result = await self.session.execute(
            select(User).where(User.email == payload.email)
        )
        user = result.scalars().first()

        if user:
            token = generate_reset_token(user.email)
            send_reset_email_background(user.email, token, background_tasks)

        return {
            "status": "success",
            "message": "If an account with that email exists, a password reset link has been sent.",
        }

    async def reset_password(self, payload: ResetPasswordSchema) -> dict:
        email = verify_reset_token(payload.token, max_age=3600)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The password reset link is invalid or has expired.",
            )

        try:
            user = await self.user_manager.get_by_email(email)
        except UserNotExists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account associated with this token was not found.",
            )

        hashed_password = self.user_manager.password_helper.hash(
            payload.new_password)
        await self.user_manager.user_db.update(
            user, {"hashed_password": hashed_password}
        )

        return {
            "status": "success",
            "message": "Your password has been successfully reset. You can now log in.",
        }

    async def change_password(self, user: User, payload: ChangePassword) -> dict:
        is_valid, _ = self.user_manager.password_helper.verify_and_update(
            payload.current_password, user.hashed_password
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password.",
            )

        new_hashed_password = self.user_manager.password_helper.hash(
            payload.new_password)
        await self.user_manager.user_db.update(
            user, {"hashed_password": new_hashed_password}
        )

        return {
            "status": "success",
            "message": "Your password has been changed successfully.",
        }
