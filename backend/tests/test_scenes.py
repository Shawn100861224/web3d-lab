"""模块 2 验收测试：/api/scenes 的空结果路径、写入、过滤、错误码。"""

from __future__ import annotations


def test_empty_library_returns_200_not_404(client):
    r = client.get("/api/scenes")
    assert r.status_code == 200
    assert r.json() == {"total": 0, "items": []}


def test_create_then_read_back(client, scene_payload):
    created = client.post("/api/scenes", json=scene_payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["id"] > 0
    assert body["slug"] == "desk-chair"
    assert body["psnr"] == 27.84
    assert body["asset_format"] == "spz"

    listed = client.get("/api/scenes")
    assert listed.status_code == 200
    doc = listed.json()
    assert doc["total"] == 1
    assert doc["items"][0]["slug"] == "desk-chair"

    detail = client.get("/api/scenes/desk-chair")
    assert detail.status_code == 200
    assert detail.json()["num_points"] == 412_345


def test_unknown_slug_is_404_with_detail(client):
    r = client.get("/api/scenes/does-not-exist")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


def test_duplicate_slug_is_409(client, scene_payload):
    assert client.post("/api/scenes", json=scene_payload).status_code == 201
    again = client.post("/api/scenes", json=scene_payload)
    assert again.status_code == 409
    assert "already exists" in again.json()["detail"]


def test_missing_required_field_is_422(client, scene_payload):
    bad = {k: v for k, v in scene_payload.items() if k != "asset_url"}
    assert client.post("/api/scenes", json=bad).status_code == 422


def test_filter_by_technique_and_featured(client, scene_payload):
    client.post("/api/scenes", json=scene_payload)
    other = dict(scene_payload, slug="mug-2dgs", technique="2DGS", featured=False)
    client.post("/api/scenes", json=other)

    only_3dgs = client.get("/api/scenes", params={"technique": "3DGS"}).json()
    assert only_3dgs["total"] == 1
    assert only_3dgs["items"][0]["technique"] == "3DGS"

    featured = client.get("/api/scenes", params={"featured": True}).json()
    assert featured["total"] == 1
    assert featured["items"][0]["slug"] == "desk-chair"

    assert client.get("/api/scenes", params={"technique": "Mip-Splatting"}).json() == {
        "total": 0,
        "items": [],
    }


def test_pagination_bounds(client, scene_payload):
    for i in range(3):
        client.post("/api/scenes", json=dict(scene_payload, slug=f"scene-{i}"))

    page = client.get("/api/scenes", params={"limit": 2, "offset": 0}).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2

    rest = client.get("/api/scenes", params={"limit": 2, "offset": 2}).json()
    assert len(rest["items"]) == 1

    # 越界参数由 Query(ge/le) 拦下
    assert client.get("/api/scenes", params={"limit": 0}).status_code == 422
    assert client.get("/api/scenes", params={"offset": -1}).status_code == 422


def test_unpublished_excluded_by_default(client, scene_payload):
    client.post("/api/scenes", json=dict(scene_payload, slug="draft", published=False))
    assert client.get("/api/scenes").json()["total"] == 0
    drafts = client.get("/api/scenes", params={"published": False}).json()
    assert drafts["total"] == 1
