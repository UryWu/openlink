"""Regex file content search."""

import asyncio
import os
import re
from pathlib import Path

from app.core.security.sandbox import safe_path, safe_abs_path
from app.tools.base import BaseTool, ToolContext, ToolResult

_MAX_RESULTS = 100


class GrepTool(BaseTool):
    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search file contents using regex"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "pattern": "string (required) - regex pattern to search",
            "path": "string (optional) - directory to search (default: root)",
            "include": "string (optional) - file glob filter, e.g. *.py",
        }

    def validate(self, args: dict) -> str | None:
        p = args.get("pattern")
        if not isinstance(p, str) or not p.strip():
            return "pattern is required"
        inc = args.get("include")
        if isinstance(inc, str) and ("/" in inc or "\\" in inc):
            return "include pattern must not contain path separators"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        pattern: str = ctx.args["pattern"]
        search_path: str = ctx.args.get("path", ".")
        include: str | None = ctx.args.get("include")
        root = ctx.config.root_dir

        # Resolve search path through sandbox
        try:
            if os.path.isabs(search_path) or search_path.startswith("~"):
                safe = safe_abs_path(
                    search_path,
                    allowed_roots=[root, str(Path.home() / ".claude"),
                                   str(Path.home() / ".openlink"),
                                   str(Path.home() / ".agent")],
                )
            else:
                safe = safe_path(root, search_path)
        except ValueError as e:
            return ToolResult(status="error", error=str(e))

        # Try rg (ripgrep) first
        output = await self._try_rg(pattern, safe, include)
        if output is not None:
            return ToolResult(output=output)

        # Fallback to native Python grep
        try:
            output = await self._grep_native(pattern, safe, include)
            return ToolResult(output=output)
        except ValueError as e:
            return ToolResult(status="error", error=str(e))

    async def _try_rg(self, pattern: str, search_path: str, include: str | None) -> str | None:
        """Use ripgrep if available. Returns None if rg not found."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "rg", "-n", "--no-heading",
                *(("--glob", include) if include else ()),
                "--", pattern, search_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except FileNotFoundError:
            return None

        stdout, _ = await proc.communicate()
        lines = stdout.decode("utf-8", errors="replace").splitlines()
        return self._format_lines(lines)

    async def _grep_native(self, pattern: str, search_path: str, include: str | None) -> str:
        """Native Python grep walk (ripgrep not assumed installed)."""
        try:
            re_compiled = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"invalid pattern: {e}") from e

        matches: list[tuple[str, float]] = []  # (line_text, mtime)

        for root_dir, _dirs, files in os.walk(search_path):
            for fname in files:
                if include is not None:
                    if not Path(fname).match(include):
                        continue
                fpath = os.path.join(root_dir, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                except OSError:
                    continue

                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            if re_compiled.search(line.rstrip("\n\r")):
                                rel = os.path.relpath(fpath, search_path)
                                matches.append((f"{rel}:{lineno}:{line.rstrip()}", mtime))
                except OSError:
                    continue

                if len(matches) >= _MAX_RESULTS * 2:
                    break

        # Sort by modification time descending (newest first)
        matches.sort(key=lambda m: m[1], reverse=True)

        lines = [m[0] for m in matches]
        return self._format_lines(lines)

    @staticmethod
    def _format_lines(lines: list[str]) -> str:
        """Format grep output, capped at MAX_RESULTS."""
        out: list[str] = []
        count = 0
        for line in lines:
            if not line.strip():
                continue
            out.append(line)
            count += 1
            if count >= _MAX_RESULTS:
                out.append(f"(结果已截断，仅显示前 {_MAX_RESULTS} 条)")
                break
        if not out:
            return "No matches found"
        return "\n".join(out)
