"""各功能的提示词模板。"""

PLATFORMS = {
    "wechat": {
        "name": "微信公众号",
        "style": "结构完整、有小标题，开头用场景或痛点切入，结尾有总结和互动引导，篇幅可较长，语气真诚有观点。",
    },
    "xiaohongshu": {
        "name": "小红书",
        "style": "标题带数字或情绪钩子，开头一句抓人，短段落加适量 emoji，干货用清单呈现，结尾带 3-5 个话题标签。",
    },
    "twitter": {
        "name": "推特/X",
        "style": "单条不超过 140 个汉字，观点鲜明、信息密度高；可拆成 3-6 条的 thread，首条要有钩子。",
    },
}

SYSTEM_BASE = (
    "你是一名资深的中文内容运营专家，熟悉公众号、小红书、推特的内容规律。"
    "输出使用 Markdown，直接给结果，不要寒暄，不要解释你的步骤。"
)


def build(kind: str, p: dict) -> tuple[str, str]:
    if kind == "topics":
        user = (
            f"赛道/领域：{p['niche']}\n目标读者：{p.get('audience') or '泛读者'}\n"
            f"请给出 {p['count']} 个有传播潜力的选题。每个选题包含：标题方向、切入角度、"
            "为什么读者会点开（一句话）。按编号列出。"
        )
    elif kind == "outline":
        plat = PLATFORMS[p["platform"]]
        user = (
            f"主题：{p['topic']}\n目标读者：{p.get('audience') or '泛读者'}\n"
            f"发布平台：{plat['name']}（风格：{plat['style']}）\n"
            "请输出一份文章大纲：开头钩子、3-5 个核心段落（每段含要点和可用案例/数据方向）、结尾与互动设计。"
        )
    elif kind == "titles":
        user = (
            f"主题：{p['topic']}\n请写 {p['count']} 个标题，覆盖不同套路"
            "（数字型、反常识型、痛点型、悬念型、对比型），每个标题后用括号标注套路类型。"
        )
    elif kind == "rewrite":
        plat = PLATFORMS[p["platform"]]
        user = (
            f"请把下面的内容改写成适合【{plat['name']}】发布的版本。\n"
            f"平台风格要求：{plat['style']}\n保留核心信息，不要编造事实。\n\n原文：\n{p['text']}"
        )
    else:
        raise ValueError(f"未知功能：{kind}")
    return SYSTEM_BASE, user
