"""Ask user question — mirrors internal/tool/question.go."""

from app.tools.base import BaseTool, ToolContext, ToolResult


class QuestionTool(BaseTool):
    @property
    def name(self) -> str:
        return "question"

    @property
    def description(self) -> str:
        return "Ask the user a question and wait for input"

    @property
    def parameters(self) -> dict[str, str]:
        return {
            "question": "string (required) - the question to ask",
            "options": "array (optional) - list of choices to present",
        }

    def validate(self, args: dict) -> str | None:
        q = args.get("question")
        if not isinstance(q, str) or not q.strip():
            return "question is required"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        question: str = ctx.args["question"]
        options = ctx.args.get("options", [])

        parts = ["[需要您的输入]\n\n", question]

        if options:
            parts.append("\n\n可选项：")
            for i, opt in enumerate(options, 1):
                parts.append(f"\n  {i}. {opt}")
            parts.append("\n\n请输入您的选择或回答：")

        return ToolResult(output="".join(parts))
