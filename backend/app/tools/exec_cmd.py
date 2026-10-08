"""Execute shell command in sandbox."""

import asyncio
import os
import sys
from datetime import datetime

from app.core.security.sandbox import is_dangerous_command
from app.tools.base import BaseTool, ToolContext, ToolResult
from app.utils.truncate import truncate


def _enable_ansi() -> bool:
    """Enable VT processing on Windows consoles; return True if color is usable."""
    if os.environ.get("NO_COLOR"):
        return False
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


_COLOR = _enable_ansi()

_RESET = "\033[0m" if _COLOR else ""
_BOLD = "\033[1m" if _COLOR else ""
_DIM = "\033[2m" if _COLOR else ""
_RED = "\033[31m" if _COLOR else ""
_GREEN = "\033[32m" if _COLOR else ""
_YELLOW = "\033[33m" if _COLOR else ""
_BLUE = "\033[34m" if _COLOR else ""
_MAGENTA = "\033[35m" if _COLOR else ""
_CYAN = "\033[36m" if _COLOR else ""


def _c(text: str, color: str, bold: bool = False) -> str:
    if not _COLOR:
        return text
    prefix = (_BOLD if bold else "") + color
    return f"{prefix}{text}{_RESET}"


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
        print(
            f"{_c(_now(), _DIM)} "
            f"{_c(f'=== [cmd #{job_id}]', _CYAN, bold=True)} "
            f"{_c('start:', _CYAN)} {_c(cmd, _BOLD)} "
            f"{_c('===', _CYAN)}"
        )
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
                    ts = _c(_now(), _DIM)
                    if prefix == "stdout":
                        tag = _c("[stdout]", _GREEN)
                    elif prefix == "stderr":
                        tag = _c("[stderr]", _RED, bold=True)
                    elif prefix:
                        tag = _c(f"[{prefix}]", _YELLOW)
                    else:
                        tag = ""
                    body = _c(decoded, _RED) if prefix == "stderr" else decoded
                    if tag:
                        print(f"{ts} {tag} {body}", end="")
                    else:
                        print(f"{ts} {body}", end="")
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
                print(
                    f"{_c(_now(), _DIM)} "
                    f"{_c(f'=== [cmd #{job_id}] done:', _RED, bold=True)} "
                    f"{_c('timeout', _RED, bold=True)} {_c('===', _RED)}"
                )
                sys.stdout.flush()
                return ToolResult(status="error", error="execution timeout")

            output_str = "".join(output_lines)
            truncated, _ = truncate(output_str)

            if proc.returncode != 0:
                print(
                    f"{_c(_now(), _DIM)} "
                    f"{_c(f'=== [cmd #{job_id}] done:', _RED, bold=True)} "
                    f"{_c(f'exit {proc.returncode}', _RED, bold=True)} {_c('===', _RED)}"
                )
                sys.stdout.flush()
                return ToolResult(status="error", error=f"exit code {proc.returncode}", output=truncated)

            print(
                f"{_c(_now(), _DIM)} "
                f"{_c(f'=== [cmd #{job_id}] done:', _GREEN, bold=True)} "
                f"{_c('exit 0', _GREEN, bold=True)} {_c('===', _GREEN)}"
            )
            sys.stdout.flush()
            if not truncated:
                truncated = "empty"
            return ToolResult(output=f"command: {cmd}\n\n{truncated}")

        except FileNotFoundError:
            print(
                f"{_c(_now(), _DIM)} "
                f"{_c(f'=== [cmd #{job_id}] done:', _RED, bold=True)} "
                f"{_c('error: shell not found', _RED)} {_c('===', _RED)}"
            )
            sys.stdout.flush()
            return ToolResult(status="error", error=f"shell not found: {shell}")
        except OSError as e:
            print(
                f"{_c(_now(), _DIM)} "
                f"{_c(f'=== [cmd #{job_id}] done:', _RED, bold=True)} "
                f"{_c(f'error: {e}', _RED)} {_c('===', _RED)}"
            )
            sys.stdout.flush()
            return ToolResult(status="error", error=str(e))
        finally:
            if bat_path is not None:
                try:
                    os.remove(bat_path)
                except OSError:
                    pass