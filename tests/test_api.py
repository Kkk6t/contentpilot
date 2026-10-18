import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    # 每个用例使用独立的临时数据库，互不影响
    monkeypatch.setenv("CONTENTPILOT_DB", str(tmp_path / "history.db"))


def test_health_demo():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["mode"] == "demo"


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "ContentPilot" in r.text


def test_topics_count():
    r = client.post("/api/topics", json={"niche": "AI 工具", "count": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "demo"
    assert "3." in body["result"] and "4." not in body["result"]


def test_demo_topics_are_not_repetitive():
    r = client.post("/api/topics", json={"niche": "AI 工具", "count": 8})
    reasons = [l for l in r.json()["result"].splitlines() if "点开理由" in l]
    assert len(reasons) == 8
    assert len(set(reasons)) == 8


def test_demo_rewrite_uses_input_sentences():
    r = client.post(
        "/api/rewrite",
        json={"text": "先选一个场景。坚持每天使用。每周复盘一次。", "platform": "xiaohongshu"},
    )
    result = r.json()["result"]
    assert "坚持每天使用" in result and "每周复盘一次" in result


def test_demo_outline_without_audience_is_clean():
    r = client.post("/api/outline", json={"topic": "AI 变现", "platform": "wechat"})
    assert "目标读者：读者" not in r.json()["result"]


def test_outline():
    r = client.post("/api/outline", json={"topic": "AI 变现", "platform": "wechat"})
    assert r.status_code == 200
    assert "AI 变现" in r.json()["result"]


def test_titles_count():
    r = client.post("/api/titles", json={"topic": "副业", "count": 4})
    assert r.status_code == 200
    assert "4." in r.json()["result"] and "5." not in r.json()["result"]


@pytest.mark.parametrize("platform", ["wechat", "xiaohongshu", "twitter"])
def test_rewrite_platforms(platform):
    r = client.post("/api/rewrite", json={"text": "这是一段原文", "platform": platform})
    assert r.status_code == 200
    assert r.json()["result"]


def test_validation_rejects_empty():
    assert client.post("/api/topics", json={"niche": ""}).status_code == 422
    assert client.post("/api/titles", json={"topic": "x", "count": 99}).status_code == 422
    assert client.post("/api/rewrite", json={"text": "x", "platform": "weibo"}).status_code == 422


def test_live_mode_uses_llm(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    async def fake_chat(system, user, temperature=0.8):
        return "来自模型的结果"

    monkeypatch.setattr(llm, "chat", fake_chat)
    r = client.post("/api/titles", json={"topic": "副业"})
    body = r.json()
    assert body["mode"] == "live"
    assert body["result"] == "来自模型的结果"
    assert isinstance(body["history_id"], int)


def test_live_mode_error_returns_502(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    async def boom(system, user, temperature=0.8):
        raise llm.LLMError("模型服务返回 401")

    monkeypatch.setattr(llm, "chat", boom)
    r = client.post("/api/titles", json={"topic": "副业"})
    assert r.status_code == 502
