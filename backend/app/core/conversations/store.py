"""对话记录的 JSONL 持久化。

存储位置默认 ~/.openlink/conversations.jsonl，一行一条 JSON。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("openlink.conversations")


def _default_path() -> str:
    """默认存储路径：~/.openlink/conversations.jsonl。"""
    return os.path.join(os.path.expanduser("~"), ".openlink", "conversations.jsonl")


def append_record(record: dict[str, Any], path: str | None = None) -> None:
    """追加一条记录到 JSONL 文件。

    参数：
    record (dict): 对话记录
    path (str|None): 存储路径；默认 ~/.openlink/conversations.jsonl
    """
    p = path or _default_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_records(path: str | None = None) -> list[dict[str, Any]]:
    """读取全部记录；文件不存在返回空列表。

    参数：
    path (str|None): 存储路径；默认 ~/.openlink/conversations.jsonl

    返回：
    list[dict]: 记录列表（按写入顺序）
    """
    p = path or _default_path()
    if not os.path.isfile(p):
        return []
    out: list[dict[str, Any]] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("跳过损坏的 JSONL 行: %s", line[:80])
    return out
