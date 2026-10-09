# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")


import os
import tempfile

import pytest

from app.core.conversations import store

@pytest.fixture(autouse=True)
def isolate_base_dir(tmp_path, monkeypatch):
    """把 _base_dir 重定向到临时目录，避免污染真实 ~/.openlink。"""
    base = tmp_path / "conversations"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store, "_base_dir", lambda: str(base))
    return str(base)

def test_append_and_read_by_conv_id(isolate_base_dir):
    store.append_record({
        "ts": 1000, "platform": "chat.deepseek.com", "convId": "abc",
        "user": "hi", "assistant": "hello",
        "inputTokens": 1, "outputTokens": 2,
    })
    recs = store.read_records(conv_id="abc")
    assert len(recs) == 1
    assert recs[0]["user"] == "hi"
    assert os.path.isfile(os.path.join(isolate_base_dir, "abc.jsonl"))

def test_multiple_convs_isolated(isolate_base_dir):
    for cid in ("c1", "c2", "c3"):
        store.append_record({"ts": 1, "convId": cid, "platform": "p",
                             "user": "u-" + cid, "assistant": "a",
                             "inputTokens": 1, "outputTokens": 1})
    all_recs = store.read_records()
    assert len(all_recs) == 3
    assert {r["convId"] for r in all_recs} == {"c1", "c2", "c3"}
    assert len(store.read_records(conv_id="c1")) == 1

def test_unknown_conv_id_falls_back(isolate_base_dir):
    store.append_record({"ts": 1, "platform": "p", "user": "u", "assistant": "a",
                         "inputTokens": 1, "outputTokens": 1})
    assert os.path.isfile(os.path.join(isolate_base_dir, "_unknown.jsonl"))

def test_sanitize_unsafe_conv_id(isolate_base_dir):
    store.append_record({"ts": 1, "convId": "../evil/x", "platform": "p",
                         "user": "u", "assistant": "a",
                         "inputTokens": 1, "outputTokens": 1})
    files = [f for f in os.listdir(isolate_base_dir) if f.endswith(".jsonl")]
    assert len(files) == 1
    assert "/" not in files[0] and chr(92) not in files[0] and ".." not in files[0]

def test_read_missing_returns_empty():
    assert store.read_records(conv_id="does-not-exist") == []

def test_list_conversations_aggregates(isolate_base_dir):
    for cid, it, ot in [("c1", 10, 20), ("c1", 5, 5), ("c2", 100, 200)]:
        store.append_record({"ts": 1700000000000 + (it * 1000), "convId": cid,
                             "platform": "chat.deepseek.com",
                             "user": "u", "assistant": "a",
                             "inputTokens": it, "outputTokens": ot})
    items = store.list_conversations()
    by_cid = {i["convId"]: i for i in items}
    assert by_cid["c1"]["count"] == 2
    assert by_cid["c1"]["inputTokens"] == 15
    assert by_cid["c1"]["outputTokens"] == 25
    assert by_cid["c1"]["totalTokens"] == 40
    assert by_cid["c2"]["count"] == 1
    assert items[0]["lastTs"] >= items[-1]["lastTs"]

def test_delete_conversation(isolate_base_dir):
    store.append_record({"ts": 1, "convId": "del-me", "platform": "p",
                         "user": "u", "assistant": "a",
                         "inputTokens": 1, "outputTokens": 1})
    assert store.delete_conversation("del-me") is True
    assert store.delete_conversation("del-me") is False
    assert store.read_records(conv_id="del-me") == []
