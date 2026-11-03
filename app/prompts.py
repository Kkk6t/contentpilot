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

# 改写篇幅：每个平台的短文/长文含义不同
LENGTHS = {
    "wechat": {
        "short": "短文：400-800 字，2-3 个小标题，适合快速阅读。",
        "long": "长文：1500-2500 字，4-6 个小标题，有场景开头、观点论证、具体方法步骤、案例和总结互动。",
    },
    "xiaohongshu": {
        "short": "短笔记：200-400 字，3-5 个要点。",
        "long": "长笔记：600-1000 字，分模块讲清背景、方法步骤、避坑提醒，干货密度高。",
    },
    "twitter": {
        "short": "单条推文：不超过 140 个汉字，一条讲完。",
        "long": "长推文串（thread）：5-8 条，首条是钩子，每条一个要点，最后一条总结并引导互动。",
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
        length = LENGTHS[p["platform"]][p.get("length", "short")]
        user = (
            f"请把下面的内容改写成适合【{plat['name']}】发布的版本。\n"
            f"平台风格要求：{plat['style']}\n"
            f"篇幅要求：{length}\n"
            "保留原文的核心观点。原文较短时，请围绕核心观点合理展开（原因、方法、例子），"
            "但不要编造具体数据、人名和事实。\n\n"
            f"原文：\n{p['text']}"
        )
    else:
        raise ValueError(f"未知功能：{kind}")
    return SYSTEM_BASE, user
