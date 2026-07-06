"""Token-based authentication — mirrors internal/security/auth.go."""

import json
import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.schemas.types import Settings

OPENLINK_DIR = Path.home() / ".openlink"
SETTINGS_FILE = OPENLINK_DIR / "settings.json"
_EXEMPT_PATHS = {"/health", "/auth"}

bearer_scheme = HTTPBearer(auto_error=False)

# Global token set at startup
_server_token: str = ""


def set_server_token(token: str):
    global _server_token
    _server_token = token


def load_or_create_token() -> str:
    """Read token from ~/.openlink/settings.json or generate a new one.

    Mirrors Go's LoadOrCreateToken() — 32 random bytes → 64 hex chars.
    """
    OPENLINK_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            settings = Settings.model_validate(data)
            if settings.token:
                return settings.token
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    token = secrets.token_hex(32)
    settings = Settings(token=token, created_at=datetime.now().isoformat())
    SETTINGS_FILE.write_text(
        settings.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return token


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    """FastAPI dependency: reject if Bearer token doesn't match server token.

    Exempt paths (/health, /auth) are handled at the route level (not here).
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    token = credentials.credentials
    expected = _server_token
    # Constant-time comparison matching Go's subtle.ConstantTimeCompare
    if len(token) != len(expected) or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
