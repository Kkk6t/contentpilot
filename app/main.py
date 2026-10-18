import logging
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, llm, mock, prompts

log = logging.getLogger("contentpilot")

app = FastAPI(title="ContentPilot", description="AI 内容运营助手", version="0.2.0")

STATIC_DIR = Path(__file__).parent / "static"
Platform = Literal["wechat", "xiaohongshu", "twitter"]


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
