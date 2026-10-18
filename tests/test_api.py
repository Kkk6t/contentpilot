import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)


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
    assert r.json() == {"mode": "live", "result": "来自模型的结果"}


def test_live_mode_error_returns_502(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    async def boom(system, user, temperature=0.8):
        raise llm.LLMError("模型服务返回 401")

    monkeypatch.setattr(llm, "chat", boom)
    r = client.post("/api/titles", json={"topic": "副业"})
    assert r.status_code == 502
