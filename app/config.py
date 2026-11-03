"""模型配置的读写：网页里填的配置会写进项目根目录的 .env，并立即生效，无需重启。"""
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
KEYS = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")

# 常见的 OpenAI 兼容服务。模型名只是默认建议，服务商更新后可以在页面里自行修改。
PRESETS = [
    {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
     "model": "deepseek-chat", "key_url": "https://platform.deepseek.com/api_keys"},
    {"id": "qwen", "name": "通义千问（阿里云百炼）", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus", "key_url": "https://bailian.console.aliyun.com/"},
    {"id": "zhipu", "name": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4",
     "model": "glm-4-flash", "key_url": "https://open.bigmodel.cn/usercenter/apikeys"},
    {"id": "moonshot", "name": "Kimi（月之暗面）", "base_url": "https://api.moonshot.cn/v1",
     "model": "moonshot-v1-8k", "key_url": "https://platform.moonshot.cn/console/api-keys"},
    {"id": "siliconflow", "name": "硅基流动", "base_url": "https://api.siliconflow.cn/v1",
     "model": "deepseek-ai/DeepSeek-V3", "key_url": "https://cloud.siliconflow.cn/account/ak"},
    {"id": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1",
     "model": "gpt-4o-mini", "key_url": "https://platform.openai.com/api-keys"},
]


def env_path() -> Path:
    # 测试时可通过环境变量换成临时文件
    return Path(os.getenv("CONTENTPILOT_ENV") or ENV_PATH)


def mask(key: str) -> str:
    key = key.strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}****{key[-4:]}"


def save(values: dict) -> None:
    """更新 .env 中的 LLM_* 三项，保留文件里的其它内容和注释，并同步到当前进程。"""
    path = env_path()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = {k: v for k, v in values.items() if k in KEYS}
    out = []
    for line in lines:
        name = line.split("=", 1)[0].strip()
        if not line.lstrip().startswith("#") and name in pending:
            out.append(f"{name}={pending.pop(name)}")
        else:
            out.append(line)
    out.extend(f"{k}={v}" for k, v in pending.items())
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    for k, v in values.items():
        if k in KEYS:
            os.environ[k] = v
