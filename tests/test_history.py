import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("CONTENTPILOT_DB", str(tmp_path / "history.db"))


def _gen_titles(topic="副业", count=3):
    return client.post("/api/titles", json={"topic": topic, "count": count}).json()


def test_generation_is_saved_and_listed():
    body = _gen_titles("AI 副业")
    items = client.get("/api/history").json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == body["history_id"]
    assert items[0]["kind"] == "titles"
    assert items[0]["title"] == "AI 副业"
    assert items[0]["favorite"] is False
    assert items[0]["preview"]


def test_preview_strips_markdown_symbols():
    from app.db import make_preview

    p = make_preview("# 标题\n\n**粗体** 内容\n- 要点一\n> 引用")
    assert p == "标题 粗体 内容 要点一 引用"
    assert len(make_preview("字" * 500)) == 80


def test_list_is_newest_first_and_filters_by_kind():
    _gen_titles("第一条")
    client.post("/api/topics", json={"niche": "第二条", "count": 3})
    items = client.get("/api/history").json()["items"]
    assert [i["title"] for i in items] == ["第二条", "第一条"]
    only_topics = client.get("/api/history", params={"kind": "topics"}).json()["items"]
    assert [i["kind"] for i in only_topics] == ["topics"]


def test_detail_returns_params_and_full_result():
    hid = _gen_titles("AI 副业", 4)["history_id"]
    d = client.get(f"/api/history/{hid}").json()
    assert d["params"] == {"topic": "AI 副业", "count": 4}
    assert "4." in d["result"]


def test_favorite_toggle_and_filter():
    hid = _gen_titles()["history_id"]
    _gen_titles("另一个")
    assert client.post(f"/api/history/{hid}/favorite").json()["favorite"] is True
    favs = client.get("/api/history", params={"favorite": True}).json()["items"]
    assert [i["id"] for i in favs] == [hid]
    assert client.post(f"/api/history/{hid}/favorite").json()["favorite"] is False


def test_delete_one_and_404():
    hid = _gen_titles()["history_id"]
    assert client.delete(f"/api/history/{hid}").status_code == 200
    assert client.get(f"/api/history/{hid}").status_code == 404
    assert client.delete(f"/api/history/{hid}").status_code == 404
    assert client.post(f"/api/history/{hid}/favorite").status_code == 404


def test_clear_keeps_favorites():
    keep = _gen_titles("保留")["history_id"]
    _gen_titles("删除1")
    _gen_titles("删除2")
    client.post(f"/api/history/{keep}/favorite")
    assert client.delete("/api/history").json() == {"deleted": 2}
    items = client.get("/api/history").json()["items"]
    assert [i["id"] for i in items] == [keep]


def test_history_query_validation():
    assert client.get("/api/history", params={"kind": "bogus"}).status_code == 422
    assert client.get("/api/history", params={"limit": 0}).status_code == 422
    assert client.get("/api/history", params={"limit": 101}).status_code == 422


def test_failed_generation_is_not_saved(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    async def boom(system, user, temperature=0.8):
        raise llm.LLMError("模型服务返回 401")

    monkeypatch.setattr(llm, "chat", boom)
    assert client.post("/api/titles", json={"topic": "副业"}).status_code == 502
    assert client.get("/api/history").json()["items"] == []


def test_save_failure_does_not_break_generation(monkeypatch):
    import sqlite3

    from app import db

    def broken(*a, **k):
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(db, "add", broken)
    r = client.post("/api/titles", json={"topic": "副业"})
    assert r.status_code == 200
    assert r.json()["history_id"] is None
    assert r.json()["result"]


def test_api_keys_never_stored(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-secret-should-not-leak")

    async def fake_chat(system, user, temperature=0.8):
        return "结果"

    monkeypatch.setattr(llm, "chat", fake_chat)
    hid = client.post("/api/titles", json={"topic": "副业"}).json()["history_id"]
    assert "sk-secret" not in client.get(f"/api/history/{hid}").text
