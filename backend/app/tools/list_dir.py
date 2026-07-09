"""List directory contents."""

import os
from pathlib import Path

from app.core.security.sandbox import safe_path, safe_abs_path
from app.tools.base import BaseTool, ToolContext, ToolResult


class ListDirTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "List directory contents"

    @property
    def parameters(self) -> dict[str, str]:
        return {"path": "string (required) - directory path"}

    def validate(self, args: dict) -> str | None:
        p = args.get("path")
        if not isinstance(p, str) or not p.strip():
            return "path is required"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        raw_path: str = ctx.args["path"]
        root = ctx.config.root_dir

        try:
            if os.path.isabs(raw_path) or raw_path.startswith("~"):
                abs_path = safe_abs_path(
                    raw_path,
                    allowed_roots=[root, str(Path.home() / ".claude"),
                                   str(Path.home() / ".openlink"),
                                   str(Path.home() / ".agent")],
                )
            else:
                abs_path = safe_path(root, raw_path)

            entries = sorted(os.listdir(abs_path))
            lines = [e + "/" if os.path.isdir(os.path.join(abs_path, e)) else e for e in entries]
            return ToolResult(output="\n".join(lines))

        except (ValueError, OSError) as e:
            return ToolResult(status="error", error=str(e))
