"""对话记录的 JSONL 持久化。


布局：~/.openlink/conversations/<convId>.jsonl —— 每个会话一个文件。
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger("openlink.conversations")

SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]")

def _base_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".openlink", "conversations")

def _sanitize_conv_id(conv_id: str | None) -> str:
    s = (conv_id or "").strip()
    if not s:
        return "_unknown"
    s = SAFE_ID_RE.sub("", s)
    return s[:128] or "_unknown"

def _path_for(conv_id: str | None) -> str:
    return os.path.join(_base_dir(), f"{_sanitize_conv_id(conv_id)}.jsonl")

def append_record(record: dict[str, Any], conv_id: str | None = None) -> None:
    cid = conv_id if conv_id is not None else record.get("convId")
    p = _path_for(cid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def _read_lines(path: str) -> list[dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    out: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("跳过损坏的 JSONL 行: %s", line[:80])
    return out

def read_records(conv_id: str | None = None) -> list[dict[str, Any]]:
    if conv_id:
        return _read_lines(_path_for(conv_id))
    out: list[dict[str, Any]] = []
    base = _base_dir()
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            if not name.endswith(".jsonl"):
                continue
            out.extend(_read_lines(os.path.join(base, name)))
    return out

def list_conversations() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    base = _base_dir()
    if not os.path.isdir(base):
        return items
    for name in sorted(os.listdir(base)):
        if not name.endswith(".jsonl"):
            continue
        cid = name[:-6]
        recs = _read_lines(os.path.join(base, name))
        if not recs:
            continue
        first_ts = min(int(r.get("ts", 0) or 0) for r in recs)
        last_ts = max(int(r.get("ts", 0) or 0) for r in recs)
        platforms = {r.get("platform", "") for r in recs if r.get("platform")}
        platform = next(iter(platforms)) if len(platforms) == 1 else ",".join(sorted(platforms))
        it = sum(int(r.get("inputTokens", 0) or 0) for r in recs)
        ot = sum(int(r.get("outputTokens", 0) or 0) for r in recs)
        items.append({
            "convId": cid,
            "platform": platform,
            "count": len(recs),
            "firstTs": first_ts,
            "lastTs": last_ts,
            "inputTokens": it,
            "outputTokens": ot,
            "totalTokens": it + ot,
        })
    items.sort(key=lambda x: x["lastTs"], reverse=True)
    return items

def delete_conversation(conv_id: str) -> bool:
    p = _path_for(conv_id)
    if os.path.isfile(p):
        os.remove(p)
        return True
    return False
