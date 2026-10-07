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


def test_reject_message_containing_link(client):
    """反垃圾：各种写法的链接都拒收（限流挡不住换浏览器刷，留言板又没有审核界面）。"""
    payloads = {
        "直接 http 链接": "看这个 https://spam.example.com/a",
        "带 www": "我的站 www.spam.com",
        "裸域名": "点 spam.top 就能进",
        "空格拆开的域名": "spam . com 很好用",
        "全角点拆开的域名": "spam．cn 也不错",
        "大写与短链": "SEE HTTP://BIT.LY/XYZ",
    }
    for idx, (label, message) in enumerate(payloads.items()):
        r = client.post("/api/guestbook", json=_entry(message=message, client_id=f"spam-client-{idx}"))
        assert r.status_code == 400, f"{label} 未被拦下：{r.status_code} {r.text}"
        assert "链接" in r.json()["detail"], label

    # 拒收的留言不该落库
    assert client.get("/api/guestbook").json()["total"] == 0


def test_email_is_still_accepted(client):
    """留邮箱是正常需求，不能被误杀（判定前先把邮箱挖掉）。"""
    r = client.post("/api/guestbook", json=_entry(message="可以邮件联系我：someone@example.com"))
    assert r.status_code == 201, r.text
    listed = client.get("/api/guestbook").json()
    assert listed["total"] == 1
    assert "someone@example.com" in listed["items"][0]["message"]


def test_normal_text_with_dots_and_numbers_still_passes(client):
    """小数、文件名不应误伤。"""
    for idx, message in enumerate(["PSNR 14.44 还不错", "资产是 shoe.splat，2.04 MB", "用了 SH3 球谐"]):
        r = client.post("/api/guestbook", json=_entry(message=message, client_id=f"ok-client-{idx}"))
        assert r.status_code == 201, f"{message} 被误杀：{r.text}"
