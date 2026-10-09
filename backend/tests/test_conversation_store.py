import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import tempfile

from app.core.conversations.store import append_record, read_records


def test_append_and_read():
    """追加一条记录后应能读回。"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "conv.jsonl")
        append_record(
            {
                "ts": 1000,
                "platform": "chat.deepseek.com",
                "convId": "abc",
                "user": "hi",
                "assistant": "hello",
                "inputTokens": 1,
                "outputTokens": 1,
            },
            path=path,
        )
        recs = read_records(path=path)
        assert len(recs) == 1
        assert recs[0]["user"] == "hi"


def test_read_missing_file():
    """文件不存在时返回空列表。"""
    assert read_records(path="/nonexistent/path/x.jsonl") == []
