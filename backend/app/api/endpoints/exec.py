"""POST /exec — run a tool and return its result."""

from fastapi import APIRouter, Depends

from app.api.deps import auth_required
from app.schemas.types import ToolRequest, ToolResponse

router = APIRouter(dependencies=[auth_required])


def _get_executor():
    from app.main import _executor
    return _executor


def _fix_tab_newlines(args: dict) -> dict:
    """Fix AI model errors that write \\n as \\t in edit tool calls.

    Some LLMs encode newlines as tabs; expand them so the edit tool's
    substring replacer can find a match in the real file.
    """
    if "old_string" in args and isinstance(args["old_string"], str):
        old = args["old_string"]
        # If old_string contains \t but no \n, replace \t with \n\t
        if "\t" in old and "\n" not in old:
            args["old_string"] = old.replace("\t", "\n\t")
            if "new_string" in args and isinstance(args["new_string"], str):
                args["new_string"] = args["new_string"].replace("\t", "\n\t")
    return args


@router.post("/exec", response_model=ToolResponse)
async def exec_tool(req: ToolRequest):
    executor = _get_executor()

    # Apply tab→newline fix for edit tool
    if req.name == "edit":
        req.args = _fix_tab_newlines(req.args)

    return await executor.execute(req)
