import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    # delenv 会记住原值，用例结束后自动恢复，接口写入 os.environ 不会污染其它用例
    for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    monkeypatch.setenv("CONTENTPILOT_ENV", str(env))
    monkeypatch.setenv("CONTENTPILOT_DB", str(tmp_path / "history.db"))
    return env


def test_get_config_demo_has_presets():
    body = client.get("/api/config").json()
    assert body["mode"] == "demo" and body["has_key"] is False
    assert any(p["id"] == "deepseek" for p in body["presets"])


def test_save_config_switches_to_live_and_writes_env(isolated):
    r = client.post("/api/config", json={
        "api_key": "sk-test-1234567890", "base_url": "https://api.deepseek.com/v1/", "model": "deepseek-chat",
    })
    body = r.json()
    assert r.status_code == 200
    assert body["mode"] == "live"
    assert body["key_hint"] == "sk-****7890"          # 不回传完整 Key
    assert "sk-test-1234567890" not in r.text
    assert body["base_url"] == "https://api.deepseek.com/v1"
    text = isolated.read_text(encoding="utf-8")
    assert "LLM_API_KEY=sk-test-1234567890" in text
    assert client.get("/api/health").json()["mode"] == "live"


def test_save_keeps_comments_and_other_lines(isolated):
    isolated.write_text("# 我的注释\nOTHER=1\nLLM_API_KEY=old\n", encoding="utf-8")
    client.post("/api/config", json={"api_key": "new-key-abcdef", "model": "m"})
    text = isolated.read_text(encoding="utf-8")
    assert "# 我的注释" in text and "OTHER=1" in text
    assert "LLM_API_KEY=new-key-abcdef" in text and "old" not in text


def test_empty_key_keeps_saved_key():
    client.post("/api/config", json={"api_key": "sk-keep-12345678"})
    client.post("/api/config", json={"api_key": "", "model": "another-model"})
    body = client.get("/api/config").json()
    assert body["has_key"] and body["model"] == "another-model"


def test_clear_key_back_to_demo():
    client.post("/api/config", json={"api_key": "sk-keep-12345678"})
    body = client.post("/api/config", json={"api_key": "", "keep_key": False}).json()
    assert body["mode"] == "demo"


def test_newline_rejected():
    r = client.post("/api/config", json={"api_key": "abc\nLLM_MODEL=evil"})
    assert r.status_code == 422


def test_connection_test_success_and_failure(monkeypatch):
    seen = {}

    async def fake_chat(system, user, temperature=0.8, cfg=None):
        seen.update(cfg)
        return "成功"

    monkeypatch.setattr(llm, "chat", fake_chat)
    r = client.post("/api/config/test", json={"api_key": "k-unsaved", "model": "deepseek-chat"})
    assert r.status_code == 200 and r.json()["ok"]
    assert seen["key"] == "k-unsaved"               # 未保存的表单配置也能测试
    assert client.get("/api/config").json()["has_key"] is False

    async def boom(*a, **kw):
        raise llm.LLMError("模型服务返回 401：API Key 无效或已过期")

    monkeypatch.setattr(llm, "chat", boom)
    r = client.post("/api/config/test", json={"api_key": "bad"})
    assert r.status_code == 502 and "API Key 无效" in r.json()["detail"]


def test_connection_test_requires_key():
    assert client.post("/api/config/test", json={}).status_code == 400


def test_config_rejects_remote_clients():
    remote = TestClient(app, client=("192.168.1.20", 5000))
    assert remote.get("/api/config").status_code == 403
    assert remote.post("/api/config", json={"api_key": "x"}).status_code == 403
