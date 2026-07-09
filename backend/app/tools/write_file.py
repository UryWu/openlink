"""Write content to file."""

import os
from pathlib import Path

from app.core.security.sandbox import safe_path
from app.tools.base import BaseTool, ToolContext, ToolResult


class WriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to file"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "path": "string (required) - file path",
            "content": "string (required) - content to write",
            "mode": "string (optional) - 'append' or 'overwrite' (default)",
        }

    def validate(self, args: dict) -> str | None:
        p = args.get("path")
        if not isinstance(p, str) or not p.strip():
            return "path is required"
        c = args.get("content")
        if not isinstance(c, str):
            return "content is required"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        raw_path: str = ctx.args["path"]
        content: str = ctx.args["content"]
        mode: str = ctx.args.get("mode", "overwrite")
        root = ctx.config.root_dir

        try:
            abs_path = safe_path(root, raw_path)
        except ValueError as e:
            return ToolResult(status="error", error=str(e))

        # Ensure parent directory exists (mode 0755)
        Path(abs_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            if mode == "append":
                with open(abs_path, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content)
        except OSError as e:
            return ToolResult(status="error", error=str(e))

        return ToolResult(output="写入成功", stop_stream=True)
