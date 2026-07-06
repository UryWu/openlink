"""Glob file matching — mirrors internal/tool/glob.go."""

import os
from pathlib import Path

from app.tools.base import BaseTool, ToolContext, ToolResult

_MAX_RESULTS = 100


class GlobTool(BaseTool):
    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "pattern": "string (required) - glob pattern",
            "path": "string (optional, default '.') - search directory",
        }

    def validate(self, args: dict) -> str | None:
        p = args.get("pattern")
        if not isinstance(p, str) or not p.strip():
            return "pattern is required"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        pattern: str = ctx.args["pattern"]
        search_path: str = ctx.args.get("path", ".")
        root = Path(ctx.config.root_dir)

        # Resolve search path relative to root
        base = (root / search_path).resolve()

        if not base.exists():
            return ToolResult(status="error", error=f"path not found: {search_path}")

        results: list[Path] = []

        # Handle recursive ** patterns — match basename only
        if "**" in pattern:
            # Extract the basename part after **/
            base_pattern = Path(pattern).name
            for p in base.rglob("*"):
                if p.name == base_pattern:
                    results.append(p)
                    if len(results) >= _MAX_RESULTS:
                        break
        else:
            # Simple glob relative to search path
            for p in base.glob(pattern):
                results.append(p)
                if len(results) >= _MAX_RESULTS:
                    break

        # Sort by modification time (newest first) — matching Go behavior
        def _mtime(p: Path) -> float:
            try:
                return p.stat().st_mtime
            except OSError:
                return 0

        results.sort(key=_mtime, reverse=True)

        lines = [str(r.relative_to(root)) if r.is_relative_to(root) else str(r) for r in results]
        return ToolResult(output="\n".join(lines) if lines else "no matches found")
