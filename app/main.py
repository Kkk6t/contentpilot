from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import llm, mock, prompts

app = FastAPI(title="ContentPilot", description="AI 内容运营助手", version="0.1.0")

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
        return {"mode": "live", "result": text}
    return {"mode": "demo", "result": mock.generate(kind, params)}


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


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
