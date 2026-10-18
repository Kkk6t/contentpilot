"""OpenAI 兼容接口的极简客户端。没有配置 API Key 时由上层回退到演示模式。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


class LLMError(Exception):
    """调用大模型失败时抛出，供接口层转换成 502。"""


def _cfg() -> dict:
    return {
        "key": os.getenv("LLM_API_KEY", "").strip(),
        "base": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    }


def is_live() -> bool:
    return bool(_cfg()["key"])


def current_model() -> str:
    return _cfg()["model"]


async def chat(system: str, user: str, temperature: float = 0.8) -> str:
    cfg = _cfg()
    if not cfg["key"]:
        raise LLMError("未配置 LLM_API_KEY")
    payload = {
        "model": cfg["model"],
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {cfg['key']}"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{cfg['base']}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        raise LLMError(f"模型服务返回 {e.response.status_code}") from e
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise LLMError(f"调用模型失败：{type(e).__name__}") from e
