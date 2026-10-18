"""演示模式：没有 API Key 时，用模板生成确定性的示例结果，保证项目开箱即跑。

内容刻意写得像真实输出：每个选题的角度、理由、标题方向各不相同。
"""
import re

from .prompts import PLATFORMS

# (角度名, 切入方式, 读者为什么会点开, 标题方向)
_ANGLES = [
    ("新手避坑指南", "把最常见的 5 个错误做法列成清单，让读者对号入座",
     "读者最怕走弯路，「别人踩过的坑」天然有吸引力", "入门前先看：{n}个最容易踩的坑"),
    ("真实复盘", "用一次具体经历讲清楚投入、结果和后悔的地方",
     "真实经历比道理更可信，评论区容易产生共鸣", "我做了30天，说说真实的收获和教训"),
    ("工具清单", "整理可以直接上手的工具，并按使用顺序排好",
     "收藏价值高，读者可以拿来就用，转发率通常较好", "这{n}个工具够了：从入门到上手的顺序"),
    ("反常识观点", "挑战大家默认的做法，再给出更有效的替代方案",
     "观点冲突带来讨论，容易引发评论和转发", "大多数人做反了：{n}个被高估的做法"),
    ("零基础路线图", "给出 7 天或 30 天的可执行计划，每天一个小任务",
     "目标明确、步骤可执行，读者有「照着做就行」的安全感", "零基础也能开始：7天行动清单"),
    ("前后对比", "用同一件事「改之前 vs 改之后」的数据说明方法效果",
     "对比最直观，数字让读者快速判断值不值得学", "同样的事，换个做法效果差了好几倍"),
    ("爆款拆解", "拆解一篇同领域的高阅读内容，提炼标题、结构和节奏",
     "读者想知道「为什么别人能火」，拆解类内容学习价值强", "拆解一篇爆款：它到底做对了什么"),
    ("趋势判断", "结合最近的变化，讨论接下来 3-6 个月值得关注的方向",
     "读者担心错过机会，趋势类内容容易被收藏观望", "接下来半年，这个方向值得提前布局"),
]


def _topics(p: dict) -> str:
    niche = p["niche"]
    aud = p.get("audience") or "读者"
    blocks = []
    for i in range(p["count"]):
        tag, way, reason, title = _ANGLES[i % len(_ANGLES)]
        blocks.append(
            f"{i + 1}. **{niche}｜{tag}**\n"
            f"   - 切入角度：{way}\n"
            f"   - 点开理由：{reason}\n"
            f"   - 标题参考：{niche}，{title.format(n=3 + i % 5)}\n"
            f"   - 适合读者：{aud}"
        )
    return "\n\n".join(blocks)


def _outline(p: dict) -> str:
    topic = p["topic"]
    given = p.get("audience")
    aud = given or "读者"
    plat = PLATFORMS[p["platform"]]["name"]
    length = {"wechat": "建议 1500-2500 字", "xiaohongshu": "建议 400-700 字", "twitter": "建议拆成 4-6 条"}[p["platform"]]
    audience_note = f"　**目标读者**：{given}" if given else ""
    return (
        f"# {topic}（{plat}版大纲）\n\n"
        f"**篇幅建议**：{length}{audience_note}\n\n"
        "## 一、开头钩子\n"
        f"- 场景切入：描述一个「{aud}」在{topic}上反复卡住的真实瞬间\n"
        "- 抛出问题：为什么明明很努力，结果却总是差一点？\n"
        "- 预告价值：这篇会给出一套可以直接照做的方法\n\n"
        "## 二、核心段落\n"
        "1. **现状与痛点**：说明问题有多普遍，配一个小数据或一句真实读者留言\n"
        "2. **根本原因**：拆出 2-3 个真正的原因，而不是表面现象\n"
        "3. **方法与步骤**：分 3 步讲清楚，每一步配一个具体小例子\n"
        "4. **常见误区**：列出最容易踩的 3 个坑，以及如何绕开\n"
        "5. **一个完整案例**：用前后对比展示方法的效果\n\n"
        "## 三、结尾与互动\n"
        "- 一句话总结全文核心\n"
        "- 抛出一个能引发评论的问题，例如「你卡在哪一步？」\n"
        "- 预告下一篇内容，引导关注\n\n"
        "## 四、发布小贴士\n"
        "- 标题备选 3 个，发布前用小范围测试点击感受\n"
        "- 首图和开头第一句决定打开率，建议单独打磨"
    )


def _titles(p: dict) -> str:
    t = p["topic"]
    pool = [
        f"做{t}之前，我踩了3个坑才明白（数字型）",
        f"别再盲目做{t}了：方向错了越努力越白费（反常识型）",
        f"做{t}总是没进展？问题可能出在这一步（痛点型）",
        f"关于{t}，没人会提前告诉你的一件事（悬念型）",
        f"同样做{t}，为什么别人三天见效你却三个月没动静（对比型）",
        f"{t}入门清单：照着做就够了（数字型）",
        f"我用30天验证了{t}，结果出乎意料（悬念型）",
        f"90%的人做{t}都忽略了这个细节（数字型）",
        f"如果重新开始做{t}，我会先做这三件事（经验型）",
        f"{t}到底值不值得做？说点不好听的实话（反常识型）",
    ]
    return "\n".join(f"{i + 1}. {pool[i % len(pool)]}" for i in range(p["count"]))


def _sentences(text: str) -> list[str]:
    parts = [s.strip() for s in re.split(r"[。！？!?\n；;]+", text) if s.strip()]
    return parts or [text.strip()]


def _rewrite(p: dict) -> str:
    text = p["text"].strip()
    sents = _sentences(text)
    first = sents[0]
    rest = sents[1:] or sents
    plat = p["platform"]

    if plat == "xiaohongshu":
        points = "\n".join(f"{n} {s}" for n, s in zip(["1️⃣", "2️⃣", "3️⃣", "4️⃣"], rest[:4]))
        return (
            f"✨ {first[:20]}｜一篇讲清楚\n\n"
            f"姐妹们（兄弟们）今天认真聊聊这件事～\n\n"
            f"📌 核心就这几点：\n{points}\n\n"
            "💡 小提醒：先完成，再完美，从今天能做的最小一步开始。\n\n"
            "觉得有用就点个收藏，下次找得到～\n\n"
            "#干货分享 #成长记录 #效率提升 #经验总结"
        )
    if plat == "twitter":
        tweets = [f"1/ {first}\n\n（展开说说，一条一条看👇）"]
        for i, s in enumerate(rest[:4], start=2):
            tweets.append(f"{i}/ {s}")
        tweets.append(f"{len(tweets) + 1}/ 总结一句：先做起来，再优化。觉得有用欢迎转发，我下次继续拆。")
        return "\n\n".join(tweets)
    body = "\n".join(f"- {s}" for s in rest[:5])
    return (
        f"# {first}\n\n"
        "## 引言\n你是否也遇到过这样的情况：道理都懂，但真正动手时却不知道从哪里开始？\n\n"
        f"## 核心观点\n{first}。具体来说有以下几点：\n\n{body}\n\n"
        "## 怎么落地\n与其收藏十篇文章，不如今天就选一个最小的动作去做，做完再复盘。\n\n"
        "## 小结\n把关键点落到行动上，比单纯了解更有价值。欢迎在评论区聊聊你的看法。"
    )


def generate(kind: str, p: dict) -> str:
    body = {"topics": _topics, "outline": _outline, "titles": _titles, "rewrite": _rewrite}[kind](p)
    return body + "\n\n> 演示模式输出：配置 LLM_API_KEY 后，将由大模型根据你的输入生成真实内容。"
