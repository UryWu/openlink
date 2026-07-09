"""Fallback for unknown tool calls (returns a clear error to the LLM)."""

from app.tools.base import BaseTool, ToolContext, ToolResult


class InvalidTool(BaseTool):
    def __init__(self, requested_name: str = "", known_tools: list[str] | None = None):
        self._name = requested_name or "invalid"
        self._known = known_tools or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Unknown tool — returns error listing valid tools"

    async def execute(self, ctx: ToolContext) -> ToolResult:
        valid = ", ".join(self._known) if self._known else "(none registered)"
        return ToolResult(
            status="error",
            error=f"Unknown tool: {self._name}. Available tools: {valid}",
        )
