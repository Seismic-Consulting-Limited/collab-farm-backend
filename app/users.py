import uuid
from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from app.db import User, get_user_db, VerificationStatus, InvestorType
from httpx_oauth.clients.google import GoogleOAuth2
from dotenv import load_dotenv
import os

load_dotenv()

SECRET = os.getenv("SECRET", "")

google_oauth_client = GoogleOAuth2(
    os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered")

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        print(
            f"User {user.id} has forgotten their password. Reset token: {token}")

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        print(
            f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="/auth/login")


def get_jwt_strategy():
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager, auth_backends=[auth_backend])
current_active_user = fastapi_users.current_user(active=True)


async def current_verified_investor(user: User = Depends(current_active_user)):

    if user.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Current status is '{user.verification_status.value}'. Verified account required."
        )
    return user


async def current_unsubmitted_user(user: User = Depends(current_active_user)):

    if user.verification_status != VerificationStatus.NOT_SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"KYC already submitted. Current status: '{user.verification_status.value}'."
        )
    return user

