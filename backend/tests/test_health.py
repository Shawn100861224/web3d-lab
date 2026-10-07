"""模块 1 冒烟测试：服务能起、健康检查返回预期结构。

跑法：cd backend && .venv/Scripts/python.exe -m pytest tests -q
"""

from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()


def test_health_ok():
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "web3d-lab API"
    assert "uptime_seconds" in body


def test_api_index():
    with TestClient(app) as client:
        r = client.get("/api/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


def test_root_json():
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    assert r.json()["health"] == "/api/health"
