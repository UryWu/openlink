"""Main API router — aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.endpoints.health import router as health_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.config import router as config_router
from app.api.endpoints.tools import router as tools_router
from app.api.endpoints.exec import router as exec_router
from app.api.endpoints.prompt import router as prompt_router
from app.api.endpoints.skills import router as skills_router
from app.api.endpoints.files import router as files_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(config_router)
api_router.include_router(tools_router)
api_router.include_router(exec_router)
api_router.include_router(prompt_router)
api_router.include_router(skills_router)
api_router.include_router(files_router)
