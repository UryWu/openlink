import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import tempfile

from fastapi.testclient import TestClient

from app.main import app
from app.core.conversations import store
from app.core.security import auth

# 测试环境：禁用 token 校验（TestClient 不触发 lifespan，_executor/_server_token 未初始化）
app.dependency_overrides[auth.verify_token] = lambda: None

client = TestClient(app, raise_server_exceptions=False)


def test_post_and_stats(monkeypatch):
    """POST 一条记录后 GET /stats 应反映其 token。"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "conv.jsonl")
        monkeypatch.setattr(store, "_default_path", lambda: path)

        headers = {}
        r = client.post(
            "/conversations",
            json={"platform": "chat.deepseek.com", "user": "你好", "assistant": "你好呀"},
            headers=headers,
        )
        assert r.status_code == 200
        ack = r.json()
        assert ack["status"] == "ok"
        assert ack["inputTokens"] > 0

        s = client.get("/stats", headers=headers)
        assert s.status_code == 200
        data = s.json()
        assert data["summary"]["count"] == 1
        assert data["summary"]["totalTokens"] > 0
