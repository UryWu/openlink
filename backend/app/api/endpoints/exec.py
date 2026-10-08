"""POST /exec — run a tool and return its result."""

import re

from fastapi import APIRouter, Depends

from app.api.deps import auth_required
from app.schemas.types import ToolRequest, ToolResponse

router = APIRouter(dependencies=[auth_required])


def _get_executor():
    from app.main import _executor
    return _executor


_DSML_RE = re.compile(r"[｜|]{2}\s*DSML\s*[｜|]{2}")


def _strip_dsml(value):
    if isinstance(value, str):
        return _DSML_RE.sub("", value)
    if isinstance(value, list):
        return [_strip_dsml(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_dsml(v) for k, v in value.items()}
    return value


def _strip_dsml_name(name):
    return _DSML_RE.sub("", name) if isinstance(name, str) else name


def _fix_tab_newlines(args: dict) -> dict:
    """Fix AI model errors that write \n as \t in edit tool calls.

    Some LLMs encode newlines as tabs; expand them so the edit tool's
    substring replacer can find a match in the real file.
    """
    if "old_string" in args and isinstance(args["old_string"], str):
        old = args["old_string"]
        if "\t" in old and "\n" not in old:
            args["old_string"] = old.replace("\t", "\n\t")
            if "new_string" in args and isinstance(args["new_string"], str):
                args["new_string"] = args["new_string"].replace("\t", "\n\t")
    return args


@router.post("/exec", response_model=ToolResponse)
async def exec_tool(req: ToolRequest):
    executor = _get_executor()

    req.name = _strip_dsml_name(req.name)
    req.args = _strip_dsml(req.args)

    if req.name == "edit":
        req.args = _fix_tab_newlines(req.args)

    return await executor.execute(req)