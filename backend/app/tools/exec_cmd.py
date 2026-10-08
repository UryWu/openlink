"""Execute shell command in sandbox."""

import asyncio
import os
import sys
from datetime import datetime

from app.core.security.sandbox import is_dangerous_command
from app.tools.base import BaseTool, ToolContext, ToolResult
from app.utils.truncate import truncate


def _write_temp_bat(cmd: str) -> str:
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".bat", prefix="openlink_")
    os.close(fd)
    body = cmd.encode("utf-8", errors="replace")
    with open(path, "wb") as f:
        f.write(b"@echo off\r\nchcp 65001 >nul\r\n")
        f.write(body)
        f.write(b"\r\n")
    return path


class ExecCmdTool(BaseTool):
    def __init__(self, config):
        self._config = config
        self._seq = 0

    def _next_id(self) -> int:
        self._seq += 1
        return self._seq

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

        # Determine shell for the current platform
        bat_path = None
        if sys.platform == "win32":
            comspec = os.environ.get("COMSPEC", "cmd.exe")
            shell, flag = comspec, "/C"
            bat_path = _write_temp_bat(cmd)
            cmd_arg = bat_path
        else:
            shell, flag = "sh", "-c"
            cmd_arg = cmd

        env = os.environ.copy()
        for var in ("VIRTUAL_ENV", "VIRTUAL_ENV_PROMPT", "UV_PROJECT_ENVIRONMENT", "CONDA_PREFIX"):
            env.pop(var, None)

        def _now() -> str:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        job_id = self._next_id()
        print(f"{_now()} === [cmd #{job_id}] start: {cmd} ===")
        sys.stdout.flush()

        try:
            if bat_path is not None:
                spawn_args = (cmd_arg,)
            else:
                spawn_args = (shell, flag, cmd_arg)

            proc = await asyncio.create_subprocess_exec(
                *spawn_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=ctx.config.root_dir,
                env=env,
            )

            output_lines = []

            async def read_stream(stream, prefix=""):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    output_lines.append(decoded)
                    ts = _now()
                    if prefix:
                        print(f"{ts} [{prefix}] {decoded}", end="")
                    else:
                        print(f"{ts} {decoded}", end="")
                    sys.stdout.flush()

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(proc.stdout, "stdout"),
                        read_stream(proc.stderr, "stderr"),
                    ),
                    timeout=timeout,
                )
                await proc.wait()
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                print(f"{_now()} === [cmd #{job_id}] done: timeout ===")
                sys.stdout.flush()
                return ToolResult(status="error", error="execution timeout")

            output_str = "".join(output_lines)
            truncated, _ = truncate(output_str)

            if proc.returncode != 0:
                print(f"{_now()} === [cmd #{job_id}] done: exit {proc.returncode} ===")
                sys.stdout.flush()
                return ToolResult(status="error", error=f"exit code {proc.returncode}", output=truncated)

            print(f"{_now()} === [cmd #{job_id}] done: exit 0 ===")
            sys.stdout.flush()
            if not truncated:
                truncated = "empty"
            return ToolResult(output=f"command: {cmd}\n\n{truncated}")

        except FileNotFoundError:
            print(f"{_now()} === [done] error: shell not found ===")
            sys.stdout.flush()
            return ToolResult(status="error", error=f"shell not found: {shell}")
        except OSError as e:
            print(f"{_now()} === [done] error: {e} ===")
            sys.stdout.flush()
            return ToolResult(status="error", error=str(e))
        finally:
            if bat_path is not None:
                try:
                    os.remove(bat_path)
                except OSError:
                    pass