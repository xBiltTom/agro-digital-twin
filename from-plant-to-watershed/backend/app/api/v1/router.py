from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.profile import router as profile_router
from app.api.v1.simulations import router as simulations_router
from app.api.v1.twin_ws import router as twin_ws_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(profile_router)
api_router.include_router(simulations_router)
api_router.include_router(twin_ws_router)
api_router.include_router(reports_router)
