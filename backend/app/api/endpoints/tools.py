"""GET /tools — mirrors server.go handleListTools."""

from fastapi import APIRouter, Depends

from app.api.deps import auth_required

router = APIRouter(dependencies=[auth_required])


def _get_executor():
    from app.main import _executor
    return _executor


@router.get("/tools")
async def list_tools():
    executor = _get_executor()
    return {"tools": executor.list_tools()}
