"""Pydantic models for tool request/response and runtime config."""

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class ToolRequest(BaseModel):
    """Incoming tool call from the browser extension."""
    name: str
    args: dict[str, Any] = {}
    arguments: Optional[dict[str, Any]] = None  # alias accepted by API
    reason: Optional[str] = None
    syntax_warning: Optional[str] = Field(default=None, alias="_syntaxWarning")

    model_config = {"populate_by_name": True}

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
    version: str = "1.4.0"


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


class ConversationIn(BaseModel):
    """扩展上报的一条对话记录（未含 token）。"""
    platform: str
    convId: Optional[str] = None
    user: str = ""
    assistant: str = ""


class ConversationAck(BaseModel):
    """POST /conversations 响应。"""
    status: str = "ok"
    inputTokens: int = 0
    outputTokens: int = 0


class SummaryStats(BaseModel):
    """汇总统计。"""
    count: int = 0
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0
    cost: float = 0.0


class DayStat(BaseModel):
    """按天统计。"""
    date: str
    inputTokens: int = 0
    outputTokens: int = 0
    cost: float = 0.0


class PlatformStat(BaseModel):
    """按平台统计。"""
    platform: str
    count: int = 0
    tokens: int = 0
    cost: float = 0.0


class RecentItem(BaseModel):
    """最近对话条目。"""
    ts: int
    platform: str
    user: str = ""
    inputTokens: int = 0
    outputTokens: int = 0


class ClusterStat(BaseModel):
    """按时间间隔聚类的会话组统计。"""
    startTime: int
    endTime: int
    count: int
    inputTokens: int
    outputTokens: int
    totalTokens: int
    cost: float = 0.0


class StatsResponse(BaseModel):
    """GET /stats 响应。"""
    currency: str = "CNY"
    summary: SummaryStats
    byDay: list[DayStat] = []
    byHour: list[DayStat] = []
    byWeek: list[DayStat] = []
    byMonth: list[DayStat] = []
    byYear: list[DayStat] = []
    byPlatform: list[PlatformStat] = []
    clusters: list[ClusterStat] = []
    recent: list[RecentItem] = []



class ConversationMeta(BaseModel):
    """会话列表条目。"""
    convId: str
    platform: str = ""
    count: int = 0
    firstTs: int = 0
    lastTs: int = 0
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0

class ConversationListResponse(BaseModel):
    """GET /conversations 响应。"""
    items: list[ConversationMeta] = []

class DeleteAck(BaseModel):
    """DELETE /conversations/{convId} 响应。"""
    status: str = "ok"
    deleted: bool = False
