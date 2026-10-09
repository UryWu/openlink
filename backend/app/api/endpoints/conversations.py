"""POST /conversations + GET /stats — 对话记录与 token 统计。"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from app.api.deps import auth_required
from app.core.conversations import store
from fastapi import HTTPException


from app.schemas.types import (
    ConversationIn,
    ConversationAck,
    ConversationListResponse,
    ConversationMeta,
    DeleteAck,
    StatsResponse,
    SummaryStats,
    DayStat,
    PlatformStat,
    RecentItem,
)
from app.utils.token_count import count_tokens

logger = logging.getLogger("openlink.conversations")

router = APIRouter(dependencies=[auth_required])


@router.post("/conversations", response_model=ConversationAck)
async def add_conversation(req: ConversationIn):
    """接收一条对话记录，计算 token 并持久化。"""
    it = count_tokens(req.user)
    ot = count_tokens(req.assistant)
    record = {
        "ts": int(time.time() * 1000),
        "platform": req.platform,
        "convId": req.convId,
        "user": req.user,
        "assistant": req.assistant,
        "inputTokens": it,
        "outputTokens": ot,
    }
    try:
        store.append_record(record)
    except Exception as exc:
        logger.exception("写入对话记录失败: %s", exc)
        return ConversationAck(status="error", inputTokens=it, outputTokens=ot)
    return ConversationAck(status="ok", inputTokens=it, outputTokens=ot)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations():
    """列出所有会话（按最后活跃时间倒序）。"""
    return ConversationListResponse(items=[ConversationMeta(**m) for m in store.list_conversations()])



@router.delete("/conversations/{conv_id}", response_model=DeleteAck)
async def delete_conversation(conv_id: str):
    ok = store.delete_conversation(conv_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"conversation not found: {conv_id}")
    return DeleteAck(status="ok", deleted=True)

@router.get("/stats", response_model=StatsResponse)
async def get_stats(convId: str | None = None):
    """聚合对话记录，返回统计；可选按 convId 过滤。"""
    records = store.read_records(conv_id=convId)

    summary = SummaryStats()
    by_day: dict[str, DayStat] = {}
    by_platform: dict[str, PlatformStat] = {}

    for r in records:
        it = int(r.get("inputTokens", 0))
        ot = int(r.get("outputTokens", 0))
        summary.count += 1
        summary.inputTokens += it
        summary.outputTokens += ot

        ts = int(r.get("ts", 0))
        date = time.strftime("%Y-%m-%d", time.localtime(ts / 1000)) if ts else "unknown"
        d = by_day.setdefault(date, DayStat(date=date))
        d.inputTokens += it
        d.outputTokens += ot

        plat = r.get("platform", "unknown")
        p = by_platform.setdefault(plat, PlatformStat(platform=plat))
        p.count += 1
        p.tokens += it + ot

    summary.totalTokens = summary.inputTokens + summary.outputTokens

    recent = [
        RecentItem(
            ts=int(r.get("ts", 0)),
            platform=r.get("platform", ""),
            user=(r.get("user", "") or "")[:100],
            inputTokens=int(r.get("inputTokens", 0)),
            outputTokens=int(r.get("outputTokens", 0)),
        )
        for r in records[-100:][::-1]
    ]

    return StatsResponse(
        summary=summary,
        byDay=sorted(by_day.values(), key=lambda x: x.date),
        byPlatform=sorted(by_platform.values(), key=lambda x: x.tokens, reverse=True),
        recent=recent,
    )
