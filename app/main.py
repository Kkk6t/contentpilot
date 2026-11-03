import logging
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, llm, mock, prompts

log = logging.getLogger("contentpilot")

app = FastAPI(title="ContentPilot", description="AI 内容运营助手", version="0.3.0")

STATIC_DIR = Path(__file__).parent / "static"
Platform = Literal["wechat", "xiaohongshu", "twitter"]
Length = Literal["short", "long"]


class TopicsReq(BaseModel):
    niche: str = Field(min_length=1, max_length=100)
    audience: str = Field(default="", max_length=100)
    count: int = Field(default=5, ge=1, le=10)


class OutlineReq(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    audience: str = Field(default="", max_length=100)
    platform: Platform = "wechat"


class TitlesReq(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    count: int = Field(default=5, ge=1, le=10)


class RewriteReq(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    platform: Platform = "xiaohongshu"
    length: Length = "short"


# 配置值会写进 .env，禁止换行，避免一行里塞进别的配置
_ONE_LINE = r"^[^\r\n]*$"


class ConfigReq(BaseModel):
    api_key: str = Field(default="", max_length=300, pattern=_ONE_LINE)
    base_url: str = Field(default="", max_length=300, pattern=_ONE_LINE)
    model: str = Field(default="", max_length=100, pattern=_ONE_LINE)
    keep_key: bool = True  # api_key 留空时保留已保存的 Key


async def _run(kind: str, params: dict) -> dict:
    if llm.is_live():
        system, user = prompts.build(kind, params)
        try:
            text = await llm.chat(system, user)
        except llm.LLMError as e:
            raise HTTPException(status_code=502, detail=str(e))
        mode = "live"
    else:
        text = mock.generate(kind, params)
        mode = "demo"

    # 历史记录写入失败不应影响本次生成结果
    history_id = None
    try:
        history_id = db.add(kind, params, text, mode)
    except (sqlite3.Error, OSError):
        log.exception("保存历史记录失败")
    return {"mode": mode, "result": text, "history_id": history_id}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "mode": "live" if llm.is_live() else "demo",
        "model": llm.current_model() if llm.is_live() else None,
    }


@app.post("/api/topics")
async def topics(req: TopicsReq):
    return await _run("topics", req.model_dump())


@app.post("/api/outline")
async def outline(req: OutlineReq):
    return await _run("outline", req.model_dump())


@app.post("/api/titles")
async def titles(req: TitlesReq):
    return await _run("titles", req.model_dump())


@app.post("/api/rewrite")
async def rewrite(req: RewriteReq):
    return await _run("rewrite", req.model_dump())


# ---------- 模型配置 ----------
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def _local_only(request: Request) -> None:
    """配置接口能读写 API Key，只允许本机访问。"""
    host = request.client.host if request.client else ""
    if host not in _LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="只能在运行服务的这台电脑上修改配置")


def _config_view() -> dict:
    cfg = llm._cfg()
    return {
        "mode": "live" if cfg["key"] else "demo",
        "has_key": bool(cfg["key"]),
        "key_hint": config.mask(cfg["key"]),
        "base_url": cfg["base"],
        "model": cfg["model"],
        "presets": config.PRESETS,
    }


def _merge(req: ConfigReq) -> dict:
    current = llm._cfg()
    key = req.api_key.strip() or (current["key"] if req.keep_key else "")
    return {
        "key": key,
        "base": (req.base_url.strip() or llm.DEFAULT_BASE).rstrip("/"),
        "model": req.model.strip() or llm.DEFAULT_MODEL,
    }


@app.get("/api/config")
async def config_get(request: Request):
    _local_only(request)
    return _config_view()


@app.post("/api/config")
async def config_save(req: ConfigReq, request: Request):
    _local_only(request)
    cfg = _merge(req)
    try:
        config.save({"LLM_API_KEY": cfg["key"], "LLM_BASE_URL": cfg["base"], "LLM_MODEL": cfg["model"]})
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"写入 .env 失败：{e}")
    return _config_view()


@app.post("/api/config/test")
async def config_test(req: ConfigReq, request: Request):
    """用表单里的配置（未保存也可以）发一条极短的请求，确认 Key、地址、模型都能用。"""
    _local_only(request)
    cfg = _merge(req)
    if not cfg["key"]:
        raise HTTPException(status_code=400, detail="请先填写 API Key")
    try:
        reply = await llm.chat("你是连接测试助手。", "只回复两个字：成功", temperature=0, cfg=cfg)
    except llm.LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True, "model": cfg["model"], "reply": reply[:50]}


Kind = Literal["topics", "outline", "titles", "rewrite"]


@app.get("/api/history")
async def history_list(
    kind: Kind | None = None,
    favorite: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
):
    return {"items": db.list_items(kind=kind, favorite_only=favorite, limit=limit)}


@app.get("/api/history/{item_id}")
async def history_get(item_id: int):
    item = db.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")
    return item


@app.post("/api/history/{item_id}/favorite")
async def history_favorite(item_id: int):
    state = db.toggle_favorite(item_id)
    if state is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"id": item_id, "favorite": state}


@app.delete("/api/history/{item_id}")
async def history_delete(item_id: int):
    if not db.delete(item_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"deleted": item_id}


@app.delete("/api/history")
async def history_clear():
    """清空所有未收藏的记录，收藏的会保留。"""
    return {"deleted": db.clear_unfavorited()}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
