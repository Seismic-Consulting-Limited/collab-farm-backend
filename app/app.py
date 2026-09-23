from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import create_db_and_tables
from app.users import auth_backend, fastapi_users, google_oauth_client, SECRET
from app.schemas.user_schema import UserRead, UserUpdate
from app.routers.profile_route import router as onboarding_router
from app.routers.auth_route import router as auth_router
from app.routers.package_route import router as packages_router
from app.routers.farmer_route import router as farmer_router
from app.routers.dashboard_route import router as dashboard_router
from app.routers.investment_route import router as investment_router
# from app.routers.walletRoute import router as wallet_router
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(title="CollabFarm", debug=True, lifespan=lifespan)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["Users"]
)
app.include_router(
    fastapi_users.get_oauth_router(google_oauth_client, auth_backend, SECRET),
    prefix="/auth/google",
    tags=["Google Authentication"]
)
app.include_router(dashboard_router)
app.include_router(onboarding_router, prefix="/onboard")
app.include_router(packages_router)
app.include_router(farmer_router)
app.include_router(investment_router)
# app.include_router(wallet_router)

