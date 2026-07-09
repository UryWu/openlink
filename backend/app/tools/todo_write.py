"""Write task list to .todos.json."""

import json
from pathlib import Path

from app.tools.base import BaseTool, ToolContext, ToolResult


class TodoWriteTool(BaseTool):
    @property
    def name(self) -> str:
        return "todo_write"

    @property
    def description(self) -> str:
        return "Write task list to .todos.json"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "todos": "array (required) - list of task items",
        }

    def validate(self, args: dict) -> str | None:
        todos = args.get("todos")
        if not isinstance(todos, (list, tuple)):
            return "todos must be an array"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        todos = ctx.args["todos"]
        root = Path(ctx.config.root_dir)
        target = root / ".todos.json"

        try:
            target.write_text(
                json.dumps(todos, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            return ToolResult(status="error", error=str(e))

        return ToolResult(output=f"已保存 {len(todos)} 个任务", stop_stream=True)
