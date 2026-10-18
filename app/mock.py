"""演示模式：没有 API Key 时，用模板生成确定性的示例结果，保证项目开箱即跑。"""
from .prompts import PLATFORMS

_ANGLES = [
    ("新手避坑", "把常见的错误做法列成清单，让读者对号入座"),
    ("真实复盘", "用一个具体的个人经历讲清楚得失"),
    ("工具清单", "整理可直接上手的工具和使用顺序"),
    ("反常识观点", "挑战大家默认的做法，再给出替代方案"),
    ("零基础路线", "给出 7 天或 30 天的可执行路线图"),
    ("数据对比", "用前后对比说明方法的效果"),
    ("案例拆解", "拆解一个同领域的爆款，提炼可复用的套路"),
    ("趋势预判", "结合最近变化，讨论接下来值得关注的方向"),
]


def _topics(p: dict) -> str:
    lines = []
    for i in range(p["count"]):
        tag, way = _ANGLES[i % len(_ANGLES)]
        lines.append(
            f"{i + 1}. **{p['niche']}：{tag}**\n"
            f"   - 切入角度：{way}\n"
            f"   - 点开理由：和「{p.get('audience') or '读者'}」的切身问题直接相关"
        )
    return "\n\n".join(lines)


def _outline(p: dict) -> str:
    plat = PLATFORMS[p["platform"]]["name"]
    return (
        f"# {p['topic']}（{plat}版大纲）\n\n"
        f"## 开头钩子\n- 用一个「{p.get('audience') or '读者'}」都经历过的场景切入\n- 抛出问题：为什么大多数人在这件事上卡住？\n\n"
        "## 核心段落\n"
        "1. **现状与痛点**：说清楚问题有多普遍，附一个小数据或案例\n"
        "2. **关键原因**：拆出 2-3 个根本原因\n"
        "3. **方法与步骤**：给出可照做的步骤，每步配一个小例子\n"
        "4. **常见误区**：列出最容易踩的 3 个坑\n\n"
        "## 结尾与互动\n- 一句话总结全文\n- 抛一个问题引导评论，并预告下一篇"
    )


def _titles(p: dict) -> str:
    t = p["topic"]
    pool = [
        f"{t}，我踩了 3 个坑才搞明白（数字型）",
        f"别再盲目做{t}了，方向错了越努力越白费（反常识型）",
        f"做{t}总是没进展？问题可能出在这一步（痛点型）",
        f"关于{t}，没人告诉过你的一件事（悬念型）",
        f"同样做{t}，为什么别人三天见效你却三个月没动静（对比型）",
        f"{t}入门清单：照着做就够了（数字型）",
        f"我用 30 天验证了{t}，结果出乎意料（悬念型）",
        f"90% 的人做{t}都忽略了这个细节（数字型）",
    ]
    return "\n".join(f"{i + 1}. {pool[i % len(pool)]}" for i in range(p["count"]))


def _rewrite(p: dict) -> str:
    text = p["text"].strip()
    short = text if len(text) <= 120 else text[:120] + "……"
    plat = p["platform"]
    if plat == "xiaohongshu":
        return (
            f"✨ 干货分享｜一篇讲清楚\n\n{short}\n\n"
            "📌 重点记这 3 点：\n1️⃣ 先明确目标\n2️⃣ 再拆成小步骤\n3️⃣ 每天复盘一次\n\n"
            "#干货分享 #成长 #效率提升"
        )
    if plat == "twitter":
        return f"1/ {short[:100]}\n\n2/ 核心结论只有一句：先做起来，再优化。\n\n3/ 觉得有用就转发，下次继续拆解。"
    return (
        f"## 引言\n你是否也遇到过这样的情况？\n\n## 正文\n{short}\n\n"
        "## 小结\n把关键点落到行动上，比收藏十篇文章更有用。欢迎在评论区聊聊你的看法。"
    )


def generate(kind: str, p: dict) -> str:
    body = {"topics": _topics, "outline": _outline, "titles": _titles, "rewrite": _rewrite}[kind](p)
    return body + "\n\n> 演示模式输出：配置 LLM_API_KEY 后将由大模型生成真实内容。"
