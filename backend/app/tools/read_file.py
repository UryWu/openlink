"""Read file contents with offset/limit — mirrors internal/tool/read_file.go."""

import os

from app.core.security.sandbox import safe_path, safe_abs_path
from app.tools.base import BaseTool, ToolContext, ToolResult
from app.utils.truncate import MAX_BYTES, MAX_LINES, truncate

_LINE_CAP = 2000
_BYTE_CAP = 50 * 1024


class ReadFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read file contents"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "path": "string (required) - file path",
            "offset": "int (optional, default 1) - starting line (1-based)",
            "limit": "int (optional, default 2000, max 2000) - max lines",
        }

    def validate(self, args: dict) -> str | None:
        p = args.get("path")
        if not isinstance(p, str) or not p.strip():
            return "path is required"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        raw_path: str = ctx.args["path"]
        offset = int(ctx.args.get("offset", 1))
        limit = int(ctx.args.get("limit", _LINE_CAP))
        if limit > _LINE_CAP:
            limit = _LINE_CAP
        root = ctx.config.root_dir

        try:
            if os.path.isabs(raw_path) or raw_path.startswith("~"):
                abs_path = safe_abs_path(
                    raw_path,
                    allowed_roots=[root, str(os.path.expanduser("~/.claude")),
                                   str(os.path.expanduser("~/.openlink")),
                                   str(os.path.expanduser("~/.agent"))],
                )
            else:
                abs_path = safe_path(root, raw_path)
        except ValueError as e:
            return ToolResult(status="error", error=str(e))

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return ToolResult(
                status="error",
                error=f"文件不存在: {raw_path} (resolved: {abs_path})",
            )
        except IsADirectoryError:
            return ToolResult(
                status="error",
                error=f"路径是目录而非文件: {raw_path}",
            )
        except PermissionError:
            return ToolResult(
                status="error",
                error=f"无权限读取: {raw_path}",
            )
        except OSError as e:
            return ToolResult(status="error", error=f"读取失败 {raw_path}: {e}")

        if offset < 1:
            offset = 1
        start = offset - 1
        selected = lines[start: start + limit]

        output = "".join(selected)
        was_truncated = False
        if len(selected) >= _LINE_CAP or len(output.encode("utf-8")) >= _BYTE_CAP:
            output, was_truncated = truncate(output)

        if was_truncated:
            pass  # truncate() already appended hint

        if not output.endswith("\n"):
            output += "\n"

        # Add line number range hint for continuation
        next_offset = offset + len(selected)
        if next_offset <= len(lines) and (len(selected) >= _LINE_CAP or was_truncated):
            output += f"\n[文件较长，使用 offset={next_offset} 继续读取]"

        return ToolResult(output=output)
