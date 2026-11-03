# ContentPilot · AI 内容运营助手

一个面向内容创作者和运营的轻量 AI 工具：输入赛道或主题，一键生成**选题、文章大纲、爆款标题**，并能把同一份内容**改写成公众号 / 小红书 / 推特**三种平台风格。

- 后端：Python + FastAPI
- 前端：原生 HTML/JS 单页（无需构建）
- 模型：任何兼容 OpenAI Chat Completions 的服务（OpenAI、DeepSeek 等）
- **没有 API Key 也能跑**：自动进入演示模式，克隆下来立刻可体验

## 功能

| 功能 | 说明 |
| --- | --- |
| 选题生成 | 按赛道和目标读者，给出多个选题、切入角度和点开理由 |
| 文章大纲 | 针对不同平台输出带钩子、核心段落和互动设计的大纲 |
| 爆款标题 | 覆盖数字型、反常识型、痛点型、悬念型、对比型等套路 |
| 多平台改写 | 同一内容改写为公众号、小红书、推特风格，可选短文 / 长文 |
| 历史记录 | 每次生成自动保存；支持查看、复制、收藏、删除，按功能或收藏筛选，一键清空未收藏 |

## 快速开始

需要 Python 3.10 及以上（命令行输入 `python --version` 确认）。

### 第一步：下载项目（二选一）

**方式 A：不会用 Git / 没装 Git（推荐新手）**

1. 在本页面点绿色的 **Code** 按钮 → **Download ZIP**
2. 解压到任意位置，例如 `D:\contentpilot-main`（打开文件夹应能直接看到 `app`、`requirements.txt`）
3. Windows 用户可以直接**双击 `start.bat`**，它会自动安装依赖并启动，跳过第二步

**方式 B：已安装 Git**

```bash
git clone https://github.com/Kkk6t/contentpilot.git
cd contentpilot
```

### 第二步：安装依赖并启动

先用 `cd` 进入项目文件夹（Windows 跨盘符要加 `/d`，例如 `cd /d D:\contentpilot-main`），然后：

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

看到 `Uvicorn running on http://127.0.0.1:8000` 后，浏览器打开 http://127.0.0.1:8000 即可使用。不填 API Key 也能跑（演示模式）。

> 为什么用 `python -m pip` 而不是 `pip`：Windows 上直接运行 `pip.exe` / `uvicorn.exe` 有时会被系统安全策略（智能应用控制 / Device Guard）拦截，或者调用到别的 Python 环境。`python -m` 的写法更稳。

### 常见问题

| 报错 | 原因与解决 |
| --- | --- |
| `'git' 不是内部或外部命令` | 没装 Git，用上面的方式 A 下载 ZIP |
| `系统找不到指定的路径` | 项目还没下载下来，或 `cd` 的路径不对 |
| `Could not open requirements file` | 当前不在项目文件夹里，先 `cd` 进去 |
| `No module named 'app'` | 同上，必须在项目根目录（能看到 `app` 文件夹的那一层）运行 |
| `...已被组织的 Device Guard 策略阻止` | 改用 `python -m pip`、`python -m uvicorn` |
| `'python' 不是内部或外部命令` | 没装 Python，或安装时没勾选 "Add Python to PATH"，去 python.org 重装并勾选 |

### 接入大模型（可选）

不配置也能用（演示模式）。想生成真实内容：

1. 点页面右上角的「⚙ 演示模式 · 点击配置模型」
2. 选服务商（内置 DeepSeek、通义千问、智谱 GLM、Kimi、硅基流动、OpenAI，也可以自定义），会自动填好接口地址和模型名
3. 粘贴 API Key（弹窗里有各家申请 Key 的链接），点「测试连接」确认能用，再点「保存」

保存后立即生效，不用重启。配置写在项目文件夹的 `.env` 里，只保存在你自己电脑上；配置接口只允许本机访问。

也可以手动配置：把 `.env.example` 复制为 `.env`（Windows 用 `copy .env.example .env`），填入 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 后重启服务。

页面右上角会显示当前是「演示模式」还是「已接入模型」。`.env` 已被 `.gitignore` 忽略，不会误提交密钥。

### 运行测试

```bash
python -m pytest -q
```

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 当前模式（演示/已接入模型） |
| POST | `/api/topics` `/api/outline` `/api/titles` `/api/rewrite` | 四个生成功能 |
| GET / POST | `/api/config` | 查看 / 保存模型配置（仅本机，Key 只返回打码后的提示） |
| POST | `/api/config/test` | 用填写的配置测试连接（不保存） |
| GET | `/api/history` | 历史列表，支持 `kind`、`favorite`、`limit` 参数 |
| GET | `/api/history/{id}` | 单条记录详情（含入参与完整结果） |
| POST | `/api/history/{id}/favorite` | 切换收藏 |
| DELETE | `/api/history/{id}` | 删除单条 |
| DELETE | `/api/history` | 清空未收藏的记录（收藏的保留） |

启动后访问 http://127.0.0.1:8000/docs 可查看自动生成的交互式接口文档。

## 项目结构

```
app/
  main.py      FastAPI 路由与请求校验
  llm.py       OpenAI 兼容接口客户端（异步，错误码翻译成可读提示）
  config.py    模型配置读写（写入 .env，即时生效）与服务商预设
  db.py        SQLite 历史记录存储（标准库，无额外依赖）
  prompts.py   各功能与各平台的提示词模板
  mock.py      演示模式的模板输出
  static/      前端单页（含自带的安全 Markdown 渲染器）
start.bat      Windows 一键启动脚本
tests/         接口测试（生成、历史记录、模型模式、异常、参数校验）
data/          运行时自动创建的 SQLite 数据库（已被 .gitignore 忽略）
```

## 设计要点

- **结果不丢**：每个功能页各自保留输入和结果，切换页面不会清空，由用户点「清空」决定。
- **可降级**：无 Key 时走演示模式，保证项目任何环境都能运行和演示。
- **接口统一**：四个功能共用一个执行入口，新增功能只需添加提示词和路由。
- **错误可控**：模型调用失败统一转换为 502 并给出可读原因，前端友好提示。
- **参数校验**：Pydantic 限制长度、数量和平台枚举，非法输入返回 422。
- **历史记录不拖累主流程**：保存失败只记日志，不影响本次生成结果；失败的生成不会写入历史。
- **隐私**：只保存用户输入的参数和生成结果，API Key 不会写入数据库。
- **前端防注入**：自带 Markdown 渲染器，先整体转义再渲染；历史列表中的用户内容一律用 `textContent` 输出。
- **测试隔离**：每个用例使用独立的临时数据库，通过环境变量 `CONTENTPILOT_DB` 切换。

## 后续规划

- 自定义账号风格（语气、禁用词）
- 内容日历与批量生成
- 流式输出

## License

MIT
