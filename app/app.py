from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import create_db_and_tables
from app.users import auth_backend, fastapi_users, google_oauth_client, SECRET
from app.schemas import UserCreate, UserRead, UserUpdate
from app.routers.onboarding import router as onboarding_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(fastapi_users.get_auth_router(
    auth_backend), prefix='/auth', tags=["auth"])



app.include_router(fastapi_users.get_register_router(
    UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(
    UserRead, UserUpdate), prefix="/users", tags=["users"])
app.include_router(fastapi_users.get_oauth_router(
    google_oauth_client, auth_backend, SECRET), prefix="/auth/google", tags=["auth"])
app.include_router(onboarding_router, prefix="/onboard")
