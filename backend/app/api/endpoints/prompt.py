"""GET /prompt — mirrors server.go handlePrompt."""

from fastapi import APIRouter, Depends, Response

from app.api.deps import auth_required

router = APIRouter(dependencies=[auth_required])


def _get_executor():
    from app.main import _executor
    return _executor


@router.get("/prompt")
async def get_prompt():
    executor = _get_executor()
    return Response(
        content=executor.get_init_prompt(),
        media_type="text/plain; charset=utf-8",
    )
