"""模块 6 验收测试：留言读写、注入原样存/渲染转义的前提、限流、分页与隐藏。"""

from __future__ import annotations


def _entry(**over):
    base = {
        "name": "同学",
        "message": "场景重建得不错",
        "scene_slug": "robot-head",
        "client_id": "guest-client-01",
    }
    base.update(over)
    return base


def test_empty_list_is_200(client):
    r = client.get("/api/guestbook")
    assert r.status_code == 200
    assert r.json() == {"total": 0, "items": []}


def test_post_then_read_back(client):
    r = client.post("/api/guestbook", json=_entry())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "同学"
    assert body["scene_slug"] == "robot-head"
    assert "client_id" not in body, "响应不应泄漏访客标识"

    listed = client.get("/api/guestbook").json()
    assert listed["total"] == 1
    assert listed["items"][0]["message"] == "场景重建得不错"


def test_script_payload_stored_verbatim_and_returned_as_data(client):
    """后端不预转义：存的是原文（含尖括号），保证数据不脏。
    真正的 XSS 防护在渲染层，由前端与 Playwright 断言。"""
    payload = "<script>alert('xss')</script>"
    assert client.post("/api/guestbook", json=_entry(message=payload)).status_code == 201
    got = client.get("/api/guestbook").json()["items"][0]["message"]
    assert got == payload
    assert "&lt;" not in got


def test_whitespace_is_trimmed(client):
    body = client.post("/api/guestbook", json=_entry(name="  张三  ", message="  你好  ")).json()
    assert body["name"] == "张三"
    assert body["message"] == "你好"


def test_rate_limit_blocks_fourth_post(client):
    for i in range(3):
        r = client.post("/api/guestbook", json=_entry(message=f"第 {i} 条"))
        assert r.status_code == 201, r.text
    blocked = client.post("/api/guestbook", json=_entry(message="第四条"))
    assert blocked.status_code == 429
    assert "Retry-After" in {k.title() for k in blocked.headers}
    assert int(blocked.headers["Retry-After"]) > 0


def test_rate_limit_is_per_client(client):
    for i in range(3):
        client.post("/api/guestbook", json=_entry(message=f"a{i}"))
    other = client.post("/api/guestbook", json=_entry(message="别人", client_id="guest-client-99"))
    assert other.status_code == 201


def test_validation_bounds(client):
    assert client.post("/api/guestbook", json=_entry(message="")).status_code == 422
    assert client.post("/api/guestbook", json=_entry(name="x" * 41)).status_code == 422
    assert client.post("/api/guestbook", json=_entry(message="y" * 601)).status_code == 422
    assert client.post("/api/guestbook", json=_entry(client_id="short")).status_code == 422


def test_filter_by_scene_and_hidden_excluded(client):
    client.post("/api/guestbook", json=_entry(scene_slug="robot-head", message="场景内留言"))
    client.post("/api/guestbook", json=_entry(scene_slug=None, message="全局留言"))

    only_scene = client.get("/api/guestbook", params={"scene_slug": "robot-head"}).json()
    assert only_scene["total"] == 1
    assert only_scene["items"][0]["message"] == "场景内留言"

    assert client.get("/api/guestbook").json()["total"] == 2


def test_pagination_bounds(client):
    assert client.get("/api/guestbook", params={"limit": 0}).status_code == 422
    assert client.get("/api/guestbook", params={"offset": -1}).status_code == 422
