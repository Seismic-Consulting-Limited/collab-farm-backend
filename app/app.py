from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.db import create_db_and_tables
from app.users import (
    auth_backend,
    fastapi_users,
    google_oauth_client,
    SECRET,
)

from app.schemas.user_schema import UserRead, UserUpdate
from app.routers.profile_route import router as onboarding_router
from app.routers.auth_route import router as auth_router
from app.routers.package_route import router as packages_router
from app.routers.farmer_route import router as farmer_router
from app.routers.cooperative_dashboard_route import (
    router as cooperative_dashboard_router
)
from app.routers.cooperative_investment_route import (
    router as cooperative_investment_router
)
from app.routers.disbursement_route import (
    router as disbursement_router
)
from app.routers.chatbot_route import router as chatbot_router
from app.routers.wallet_route import router as wallet_router
from app.routers.investor_dashboard_route import (
    router as investor_dashboard_router
)
from app.routers.investors_investment_route import (
    router as investors_investment_router
)

limiter = Limiter(
    key_func=get_remote_address
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(
    title="CollabFarm",
    debug=True,
    lifespan=lifespan,
)


app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


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
    fastapi_users.get_users_router(
        UserRead,
        UserUpdate
    ),
    prefix="/users",
    tags=["Users"],
)

app.include_router(
    fastapi_users.get_oauth_router(
        google_oauth_client,
        auth_backend,
        SECRET,
    ),
    prefix="/auth/google",
    tags=["Google Authentication"],
)

app.include_router(
    onboarding_router,
    prefix="/onboard",
)

app.include_router(cooperative_dashboard_router)

app.include_router(packages_router)

app.include_router(farmer_router)

app.include_router(cooperative_investment_router)

app.include_router(disbursement_router)

app.include_router(investor_dashboard_router)

app.include_router(wallet_router)

app.include_router(investors_investment_router)

app.include_router(chatbot_router)
