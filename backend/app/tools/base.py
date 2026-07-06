"""Abstract tool interface — mirrors internal/tool/tool.go."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ToolContext:
    """Execution context passed to every tool's execute()."""
    args: dict[str, Any]
    config: Any  # AppConfig


@dataclass
class ToolResult:
    """Result returned by a tool's execute()."""
    status: str = "success"  # "success" | "error"
    output: str = ""
    error: str | None = None
    stop_stream: bool = False
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None


class BaseTool(ABC):
    """Abstract base for all tools — mirrors Go's Tool interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    def parameters(self) -> dict[str, str]:
        """Return a dict of param_name → type/hint description."""
        return {}

    def validate(self, args: dict[str, Any]) -> str | None:
        """Validate arguments; return error string or None if valid."""
        return None

    @abstractmethod
    async def execute(self, ctx: ToolContext) -> ToolResult:
        ...
