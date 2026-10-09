# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")


from fastapi.testclient import TestClient

from app.main import app
from app.core.conversations import store
from app.core.security import auth

app.dependency_overrides[auth.verify_token] = lambda: None

client = TestClient(app, raise_server_exceptions=False)

def test_post_and_stats(monkeypatch, tmp_path):
    """POST 一条记录后 GET /stats 应反映其 token。"""
    base = tmp_path / "conversations"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store, "_base_dir", lambda: str(base))






















def test_stats_filter_by_conv_id(monkeypatch, tmp_path):
    base = tmp_path / "conversations"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store, "_base_dir", lambda: str(base))






















def test_list_and_delete_conversations(monkeypatch, tmp_path):
    base = tmp_path / "conversations"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store, "_base_dir", lambda: str(base))





















