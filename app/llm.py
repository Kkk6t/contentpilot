"""OpenAI 兼容接口的极简客户端。没有配置 API Key 时由上层回退到演示模式。"""
import os

import httpx
from dotenv import load_dotenv

from .config import ENV_PATH

load_dotenv(ENV_PATH)

DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class LLMError(Exception):
    """调用大模型失败时抛出，供接口层转换成 502。"""


def _cfg() -> dict:
    return {
        "key": os.getenv("LLM_API_KEY", "").strip(),
        "base": (os.getenv("LLM_BASE_URL", "").strip() or DEFAULT_BASE).rstrip("/"),
        "model": os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODEL,
    }


def is_live() -> bool:
    return bool(_cfg()["key"])


def current_model() -> str:
    return _cfg()["model"]


# 常见错误码翻译成用户看得懂的话
_STATUS_HINTS = {
    400: "请求被拒绝，通常是模型名称不对",
    401: "API Key 无效或已过期",
    402: "账户余额不足",
    403: "没有权限使用这个模型",
    404: "接口地址或模型名称不对",
    429: "请求太频繁或额度用完了，稍后再试",
}


async def chat(system: str, user: str, temperature: float = 0.8, cfg: dict | None = None) -> str:
    cfg = cfg or _cfg()
    if not cfg["key"]:
        raise LLMError("未配置 API Key")
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
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{cfg['base']}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        hint = _STATUS_HINTS.get(code, "模型服务出错")
        raise LLMError(f"模型服务返回 {code}：{hint}") from e
    except httpx.TimeoutException as e:
        raise LLMError("连接模型服务超时，检查网络或接口地址") from e
    except (httpx.ConnectError, httpx.ProxyError) as e:
        raise LLMError("连不上模型服务，检查接口地址是否正确") from e
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise LLMError(f"调用模型失败：{type(e).__name__}") from e
