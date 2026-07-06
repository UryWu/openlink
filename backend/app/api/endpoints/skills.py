"""GET /skills — mirrors server.go handleListSkills."""

from fastapi import APIRouter, Depends

from app.api.deps import auth_required
from app.skills.loader import load_infos

router = APIRouter(dependencies=[auth_required])


def _get_config():
    from app.main import _app_config
    return _app_config


@router.get("/skills")
async def list_skills():
    cfg = _get_config()
    infos = load_infos(cfg.root_dir)
    return {
        "skills": [
            {"name": s.get("name", ""), "description": s.get("description", "")}
            for s in infos
        ]
    }
