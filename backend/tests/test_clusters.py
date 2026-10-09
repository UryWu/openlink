import sys
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import auth

app.dependency_overrides[auth.verify_token] = lambda: None
client = TestClient(app, raise_server_exceptions=False)


def test_clusters_field():
    """GET /stats 应返回 clusters 字段（列表），且结构正确。"""
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert "clusters" in data
    assert isinstance(data["clusters"], list)
    if data["clusters"]:
        c = data["clusters"][0]
        for k in ("startTime", "endTime", "count", "inputTokens", "outputTokens", "totalTokens"):
            assert k in c


def test_clusters_interval_param():
    """clusterIntervalMinutes 参数应被接受。"""
    r = client.get("/stats?clusterIntervalMinutes=5")
    assert r.status_code == 200
    r2 = client.get("/stats?clusterIntervalMinutes=1440")
    assert r2.status_code == 200
    d5 = r.json()["clusters"]
    d1440 = r2.json()["clusters"]
    # 间隔越大，组数越少（或相等）
    assert len(d1440) <= len(d5)
