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
from fastapi.responses import PlainTextResponse
import time as _time

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

@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, offset: int = 0, limit: int = 20):
    """分页返回消息（按时间倒序）。conv_id 为 '_all' 时返回全部会话的消息。"""
    if conv_id == "_all":
        records = store.read_records()
    else:
        records = store.read_records(conv_id=conv_id)
    total = len(records)
    rev = records[::-1]
    page = rev[offset:offset + limit]
    items = [
        {
            "ts": int(r.get("ts", 0)),
            "platform": r.get("platform", ""),
            "user": (r.get("user", "") or "")[:100],
            "inputTokens": int(r.get("inputTokens", 0)),
            "outputTokens": int(r.get("outputTokens", 0)),
        }
        for r in page
    ]
    return {"total": total, "offset": offset, "limit": limit, "items": items}


@router.get("/conversations/{conv_id}/export", response_class=PlainTextResponse)
async def export_conversation(conv_id: str):
    """导出单个会话为 Markdown 文本（ts 转人类可读时间）。"""
    records = store.read_records(conv_id=conv_id)
    if not records:
        raise HTTPException(status_code=404, detail=f"conversation not found: {conv_id}")
    md = _records_to_markdown(conv_id, records)
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


def _fmt_ts(ts: int) -> str:
    """毫秒时间戳转 'YYYY-MM-DD HH:MM:SS'。"""
    if not ts:
        return "-"
    return _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(ts / 1000))


def _records_to_markdown(conv_id: str, records: list) -> str:
    """把会话记录渲染为 Markdown（参考 scripts/jsonl2md.py）。"""
    parts = [f"# 会话 {conv_id}\n"]
    for i, r in enumerate(records, 1):
        parts.append(f"## 第 {i} 轮\n")
        parts.append(f"- **时间**：{_fmt_ts(int(r.get('ts', 0) or 0))}（ts={int(r.get('ts', 0) or 0)}）")
        parts.append(f"- **平台**：{r.get('platform', '')}")
        parts.append(f"- **输入 tokens**：{int(r.get('inputTokens', 0) or 0)}")
        parts.append(f"- **输出 tokens**：{int(r.get('outputTokens', 0) or 0)}\n")
        parts.append("**用户**：\n")
        parts.append("```\n" + (r.get("user", "") or "") + "\n```\n")
        parts.append("**助手**：\n")
        parts.append("```\n" + (r.get("assistant", "") or "") + "\n```\n")
        parts.append("---\n")
    return "\n".join(parts)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(convId: str | None = None):
    """聚合对话记录，返回统计；可选按 convId 过滤。"""
    records = store.read_records(conv_id=convId)

    summary = SummaryStats()
    by_day: dict[str, DayStat] = {}
    by_hour: dict[str, DayStat] = {}
    by_week: dict[str, DayStat] = {}
    by_month: dict[str, DayStat] = {}
    by_year: dict[str, DayStat] = {}
    by_platform: dict[str, PlatformStat] = {}

    for r in records:
        it = int(r.get("inputTokens", 0))
        ot = int(r.get("outputTokens", 0))
        summary.count += 1
        summary.inputTokens += it
        summary.outputTokens += ot

        ts = int(r.get("ts", 0))
        if ts:
            lt = time.localtime(ts / 1000)
            date = time.strftime("%Y-%m-%d", lt)
            hour = time.strftime("%m-%d %H:00", lt)
            week = time.strftime("%Y-%m-%d", time.localtime(ts / 1000 - (lt.tm_wday) * 86400))
            month = time.strftime("%Y-%m", lt)
            year = time.strftime("%Y", lt)
        else:
            date = hour = week = month = year = "unknown"

        d = by_day.setdefault(date, DayStat(date=date))
        d.inputTokens += it
        d.outputTokens += ot

        h = by_hour.setdefault(hour, DayStat(date=hour))
        h.inputTokens += it
        h.outputTokens += ot

        w = by_week.setdefault(week, DayStat(date=week))
        w.inputTokens += it
        w.outputTokens += ot

        mo = by_month.setdefault(month, DayStat(date=month))
        mo.inputTokens += it
        mo.outputTokens += ot

        y = by_year.setdefault(year, DayStat(date=year))
        y.inputTokens += it
        y.outputTokens += ot

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
        for r in records[-20:][::-1]
    ]

    return StatsResponse(
        summary=summary,
        byDay=sorted(by_day.values(), key=lambda x: x.date),
        byHour=sorted(by_hour.values(), key=lambda x: x.date),
        byWeek=sorted(by_week.values(), key=lambda x: x.date),
        byMonth=sorted(by_month.values(), key=lambda x: x.date),
        byYear=sorted(by_year.values(), key=lambda x: x.date),
        byPlatform=sorted(by_platform.values(), key=lambda x: x.tokens, reverse=True),
        recent=recent,
    )
