"""Execute shell command in sandbox — mirrors internal/tool/exec_cmd.go."""

import asyncio
import os
import platform
import sys

from app.core.security.sandbox import is_dangerous_command
from app.tools.base import BaseTool, ToolContext, ToolResult
from app.utils.truncate import truncate


class ExecCmdTool(BaseTool):
    def __init__(self, config):
        self._config = config

    @property
    def name(self) -> str:
        return "exec_cmd"

    @property
    def description(self) -> str:
        return "Execute shell command in sandbox"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "command": "string (required) - shell command to execute",
        }

    def validate(self, args: dict) -> str | None:
        cmd = args.get("command") or args.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            return "command is required"
        if is_dangerous_command(cmd):
            return "dangerous command blocked"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        cmd: str = ctx.args.get("command") or ctx.args.get("cmd", "")
        timeout = ctx.config.timeout

        # Determine shell — mirrors Go's getShell()
        if sys.platform == "win32":
            comspec = os.environ.get("COMSPEC", "cmd.exe")
            shell, flag = comspec, "/C"
        else:
            shell, flag = "sh", "-c"

        try:
            proc = await asyncio.create_subprocess_exec(
                shell, flag, cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=ctx.config.root_dir,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(status="error", error="execution timeout")

            output_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            truncated, _ = truncate(output_str)

            if proc.returncode != 0:
                return ToolResult(status="error", error=f"exit code {proc.returncode}", output=truncated)

            if not truncated:
                truncated = "empty"
            return ToolResult(output=f"command: {cmd}\n\n{truncated}")

        except FileNotFoundError:
            return ToolResult(status="error", error=f"shell not found: {shell}")
        except OSError as e:
            return ToolResult(status="error", error=str(e))
