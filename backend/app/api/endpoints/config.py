"""GET /config — mirrors server.go handleConfig."""

from fastapi import APIRouter, Depends

from app.api.deps import auth_required
from app.config import AppConfig
from app.schemas.types import ServerConfig

router = APIRouter(dependencies=[auth_required])


def _get_config() -> AppConfig:
    from app.main import _app_config
    return _app_config


@router.get("/config", response_model=ServerConfig)
async def get_config():
    cfg = _get_config()
    return ServerConfig(root_dir=cfg.root_dir, timeout=cfg.timeout)
