"""Pydantic models for tool request/response and runtime config."""

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class ToolRequest(BaseModel):
    """Incoming tool call from the browser extension."""
    name: str
    args: dict[str, Any] = {}
    arguments: Optional[dict[str, Any]] = None  # alias accepted by API
    reason: Optional[str] = None

    @model_validator(mode="after")
    def merge_arguments(self):
        """Accept both 'args' and 'arguments' keys (OpenAI/Anthropic compat)."""
        if not self.args and self.arguments:
            self.args = self.arguments
        self.arguments = None
        return self


class ToolResponse(BaseModel):
    """Execution result sent back to the browser."""
    status: str  # "success" or "error"
    output: str = ""
    error: Optional[str] = None
    stop_stream: bool = Field(default=False, alias="stopStream")

    model_config = {"populate_by_name": True}


class ServerConfig(BaseModel):
    """Serializable server configuration (returned by GET /config)."""
    root_dir: str
    timeout: int


class Settings(BaseModel):
    """~/.openlink/settings.json structure."""
    token: str = ""
    created_at: str = ""


class HealthResponse(BaseModel):
    """GET /health response."""
    status: str = "ok"
    dir: str = ""
    version: str = "1.3.0"


class AuthResponse(BaseModel):
    """POST /auth response."""
    valid: bool


class ToolInfo(BaseModel):
    """Serializable tool descriptor."""
    name: str
    description: str
    parameters: dict[str, str] = {}


class SkillInfo(BaseModel):
    """Serializable skill descriptor."""
    name: str
    description: str = ""
