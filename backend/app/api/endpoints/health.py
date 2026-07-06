"""GET /health — mirrors server.go handleHealth."""

from fastapi import APIRouter

from app.config import AppConfig
from app.schemas.types import HealthResponse

router = APIRouter()


def _get_config() -> AppConfig:
    from app.main import _app_config
    return _app_config


@router.get("/health", response_model=HealthResponse)
async def health():
    cfg = _get_config()
    return HealthResponse(status="ok", dir=cfg.root_dir, version="1.2.0")
