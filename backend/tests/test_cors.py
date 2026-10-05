"""跨域（CORS）行为回归测试。

线上是「前端在静态托管、后端在别处」时，浏览器会先做预检；配错了表现为
「本地全好、一上线就接口全红」。这里把三条关键行为钉住：
  1. 白名单内的 Origin 会拿到 Access-Control-Allow-Origin；
  2. 不在白名单的 Origin **拿不到**该响应头（浏览器据此拦截）；
  3. 预检 OPTIONS 能正确回落允许的方法与请求头。

conftest 里没有把 WEB3D_CORS_ORIGINS 设成线上域名，所以这里断言的是默认的开发白名单。
"""

from __future__ import annotations

ALLOWED = "http://localhost:5173"


def test_allowed_origin_gets_cors_header(client):
    r = client.get("/api/scenes", headers={"Origin": ALLOWED})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == ALLOWED
    assert r.headers.get("access-control-allow-credentials") == "true"


def test_disallowed_origin_has_no_cors_header(client):
    r = client.get("/api/scenes", headers={"Origin": "https://evil.example.com"})
    assert r.status_code == 200  # 请求本身会成功（CORS 是浏览器侧的拦截）
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_preflight_options_returns_allowed_methods(client):
    r = client.options(
        "/api/events",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code in (200, 204), r.status_code
    assert r.headers.get("access-control-allow-origin") == ALLOWED
    assert "POST" in r.headers.get("access-control-allow-methods", "")
    assert "content-type" in r.headers.get("access-control-allow-headers", "").lower()


def test_wildcard_origin_is_not_used_with_credentials(client):
    """allow_credentials=True 时绝不能用 `*`（浏览器会直接拒绝这种组合）。"""
    r = client.get("/api/scenes", headers={"Origin": ALLOWED})
    assert r.headers.get("access-control-allow-origin") != "*"
