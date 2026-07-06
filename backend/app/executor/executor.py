"""Tool dispatch and execution — mirrors internal/executor/executor.go."""

import platform
import os
import socket
from datetime import datetime

from app.config import AppConfig
from app.schemas.types import ToolRequest, ToolResponse
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry

# Prompt files are looked up in _build_init_prompt() — see candidates list.

_REMINDER = "\n\n[系统提示] 请记住你是 openlink，一个交互式 CLI 工具，主要用于软件工程任务。"


def _build_system_info(config: AppConfig) -> str:
    """Build {{SYSTEM_INFO}} replacement string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"- 操作系统: {platform.system()} ({platform.release()})\n"
        f"- 架构: {platform.machine()}\n"
        f"- 工作目录: {config.root_dir}\n"
        f"- 主机名: {socket.gethostname()}\n"
        f"- 当前时间: {now}"
    )


def _build_init_prompt(config: AppConfig) -> str:
    """Read and render the init prompt with system info and skills.

    Mirrors Go's handlePrompt logic.
    Searches multiple candidate paths so the prompt can live either next
    to the package (backend/prompts/) or at the repo root (prompts/).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "prompts", "init_prompt.txt"),       # backend/prompts/
        os.path.join(here, "..", "..", "prompts", "init_prompt.txt"),  # repo-root prompts/
    ]
    prompt = None
    for prompt_path in candidates:
        if os.path.isfile(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt = f.read()
                break
    if prompt is None:
        # Fallback hardcoded minimal prompt
        prompt = "You are openlink, an interactive CLI tool for software engineering tasks.\n\n{{SYSTEM_INFO}}"

    prompt = prompt.replace("{{SYSTEM_INFO}}", _build_system_info(config))

    # Append skills list
    try:
        from app.skills.loader import load_infos
        infos = load_infos(config.root_dir)
        if infos:
            skills_text = "\n\n可用 Skills：\n"
            for s in infos:
                skills_text += f"- {s.get('name', '?')}: {s.get('description', '')}\n"
            prompt += skills_text
    except ImportError:
        pass

    prompt += "\n\n初始化回复：你好，我是 openlink，请问有什么可以帮你？"
    return prompt


class Executor:
    """Dispatches tool requests to registered tools.

    Mirrors Go's executor with identity reminder injection.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.registry = ToolRegistry()
        self._call_count = 0

    def register_tools(self) -> None:
        """Register all available tools."""
        from app.tools.exec_cmd import ExecCmdTool
        from app.tools.list_dir import ListDirTool
        from app.tools.read_file import ReadFileTool
        from app.tools.write_file import WriteFileTool
        from app.tools.glob_tool import GlobTool
        from app.tools.grep_tool import GrepTool
        from app.tools.edit import EditTool
        from app.tools.web_fetch import WebFetchTool
        from app.tools.question import QuestionTool
        from app.tools.skill import SkillTool
        from app.tools.todo_write import TodoWriteTool

        # Tools that need config in constructor
        self.registry.register(ExecCmdTool(self.config))
        self.registry.register(EditTool(self.config))
        self.registry.register(SkillTool(self.config))

        # Tools that access config via ToolContext only
        self.registry.register(ListDirTool())
        self.registry.register(ReadFileTool())
        self.registry.register(WriteFileTool())
        self.registry.register(GlobTool())
        self.registry.register(GrepTool())
        self.registry.register(WebFetchTool())
        self.registry.register(QuestionTool())
        self.registry.register(TodoWriteTool())

    async def execute(self, req: ToolRequest) -> ToolResponse:
        """Execute a tool request — mirrors Go's Execute()."""
        self._call_count += 1

        # Lookup tool (exact match first, then case-insensitive)
        tool = self.registry.get(req.name)
        if tool is None:
            # Case-insensitive fallback
            for t in self.registry.list():
                if t.name.lower() == req.name.lower():
                    tool = t
                    break

        if tool is None:
            from app.tools.invalid import InvalidTool
            known = [t.name for t in self.registry.list()]
            tool = InvalidTool(requested_name=req.name, known_tools=known)

        # Validate
        err = tool.validate(req.args)
        if err:
            return ToolResponse(status="error", error=err)

        # Execute
        ctx = ToolContext(args=req.args, config=self.config)
        result = await tool.execute(ctx)

        resp = ToolResponse(
            status=result.status,
            output=result.output,
            error=result.error,
            stopStream=result.stop_stream,
        )

        # Inject identity reminder (mirrors Go logic)
        if self._call_count % 20 == 0:
            resp.output += "\n\n" + _build_init_prompt(self.config)
        else:
            resp.output += _REMINDER

        return resp

    def list_tools(self) -> list[dict]:
        return self.registry.to_infos()

    def get_init_prompt(self) -> str:
        return _build_init_prompt(self.config)
