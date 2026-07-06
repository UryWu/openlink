"""Thread-safe tool registry — mirrors internal/tool/registry.go."""

from __future__ import annotations

import threading
from typing import Any

from app.tools.base import BaseTool


class ToolRegistry:
    """Map of tool name → BaseTool, safe for concurrent access."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._lock = threading.RLock()

    def register(self, tool: BaseTool) -> None:
        with self._lock:
            self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        with self._lock:
            return self._tools.get(name)

    def list(self) -> list[BaseTool]:
        with self._lock:
            return list(self._tools.values())

    def to_infos(self) -> list[dict[str, Any]]:
        """Return serializable tool descriptors (for GET /tools)."""
        with self._lock:
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
                for t in self._tools.values()
            ]
