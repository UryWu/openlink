"""POST /auth — verify the bearer token."""

import secrets

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AppConfig
from app.schemas.types import AuthResponse

router = APIRouter()

_auth_scheme = HTTPBearer(auto_error=False)


def _get_config() -> AppConfig:
    from app.main import _app_config
    return _app_config


@router.post("/auth", response_model=AuthResponse)
async def auth(credentials: HTTPAuthorizationCredentials | None = Depends(_auth_scheme)):
    cfg = _get_config()
    expected = cfg.token

    token = credentials.credentials if credentials else ""
    # Constant-time comparison to prevent timing side channels
    if len(token) != len(expected) or not secrets.compare_digest(token, expected):
        return AuthResponse(valid=False)
    return AuthResponse(valid=True)
