"""POST /exec — run a tool and return its result."""

import json
import logging
import re

from fastapi import APIRouter, Depends

from app.api.deps import auth_required
from app.schemas.types import ToolRequest, ToolResponse

# 模块级日志器：所有 /exec 的到达与异常都通过它留痕，便于排查"请求丢失"
logger = logging.getLogger("openlink.exec")

router = APIRouter(dependencies=[auth_required])


def _get_executor():
    from app.main import _executor
    return _executor


# DSML 乱码标记：全角/半角竖线 ×2 + DSML + 竖线 ×2
_DSML_RE = re.compile(r"[｜|]{2}\s*DSML\s*[｜|]{2}")


def _find_dsml(value) -> str | None:
    """递归查找值中是否含 DSML 乱码标记，返回首个命中文本，未命中返回 None。"""
    if isinstance(value, str):
        m = _DSML_RE.search(value)
        return m.group(0) if m else None
    if isinstance(value, list):
        for v in value:
            hit = _find_dsml(v)
            if hit:
                return hit
    if isinstance(value, dict):
        for v in value.values():
            hit = _find_dsml(v)
            if hit:
                return hit
    return None


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
    """执行一次工具调用。

    入口即记录请求（截断），确保"请求是否到达后端"可查；
    DSML 乱码或参数异常时返回明确错误，不再静默清洗或丢弃。
    """
    # 到达即日志：无论后续成败，先留痕，便于区分"丢包"与"执行失败"
    try:
        raw_preview = json.dumps(
            {"name": req.name, "args": req.args},
            ensure_ascii=False,
        )[:300]
    except Exception:
        raw_preview = "<unserializable>"
    logger.info("[exec] 收到请求: %s", raw_preview)

    # DSML 乱码检测：不再静默删除，直接回报错误，让前端提示用户重新生成
    dsml_hit = _find_dsml(req.name) or _find_dsml(req.args)
    if dsml_hit:
        msg = (
            "⚠ 检测到乱码标记（全角竖线×2 + DSML + 全角竖线×2），"
            "工具调用标签已被污染，无法可靠解析。请重新生成，"
            "并确保 <tool> / <parameter> 标签完整、不含此类乱码标记。"
            f"检测到的原始标记：{json.dumps(dsml_hit, ensure_ascii=False)}"
        )
        logger.warning("[exec] DSML 乱码拦截: %s", msg)
        return ToolResponse(status="error", error=msg)

    try:
        executor = _get_executor()

        if req.name == "edit":
            req.args = _fix_tab_newlines(req.args)

        return await executor.execute(req)
    except Exception as exc:
        # 兜底：任何未预期异常都返回结构化错误，避免 500 静默
        logger.exception("[exec] 执行异常: %s", exc)
        return ToolResponse(status="error", error=f"[OpenLink 后端异常] {exc}")
