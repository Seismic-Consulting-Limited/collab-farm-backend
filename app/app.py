from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import create_db_and_tables
from app.users import auth_backend, fastapi_users, google_oauth_client, SECRET
from app.schemas.user import UserRead, UserUpdate
from app.routers.onboarding import router as onboarding_router
from app.routers.auth import router as auth_router
from app.routers.packages import router as packages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"]
)
app.include_router(
    fastapi_users.get_oauth_router(google_oauth_client, auth_backend, SECRET),
    prefix="/auth/google",
    tags=["auth_google"]
)
app.include_router(onboarding_router, prefix="/onboard")
app.include_router(packages_router)

