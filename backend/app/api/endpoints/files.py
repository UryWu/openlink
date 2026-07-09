"""GET /files?q= — list files under root_dir matching the query."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app.api.deps import auth_required

router = APIRouter(dependencies=[auth_required])

# Directories to skip
_SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "vendor"}
_MAX_FILES = 50


def _get_config():
    from app.main import _app_config
    return _app_config


@router.get("/files")
async def list_files(q: str = Query(default="", max_length=200)):
    cfg = _get_config()
    root = Path(cfg.root_dir)

    try:
        abs_root = root.resolve(strict=True)
    except (OSError, ValueError):
        return {"files": []}

    results: list[str] = []
    q_lower = q.lower()

    for entry in sorted(abs_root.rglob("*")):
        if entry.is_dir():
            continue
        try:
            rel = entry.relative_to(abs_root)
        except ValueError:
            continue

        # Check parent dirs for skip list
        skip = False
        for part in entry.relative_to(abs_root).parts:
            if part in _SKIP_DIRS:
                skip = True
                break
        if skip:
            continue

        rel_str = str(rel.as_posix())
        if q_lower and q_lower not in rel_str.lower():
            continue

        results.append(rel_str)
        if len(results) >= _MAX_FILES:
            break

    return {"files": results}
