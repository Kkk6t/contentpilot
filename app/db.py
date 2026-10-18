"""历史记录存储：基于标准库 sqlite3，无需额外依赖。

数据库路径由环境变量 CONTENTPILOT_DB 指定，默认放在项目的 data/history.db。
每次调用单独开关连接，简单可靠；单机轻量使用场景下足够。
"""
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    params      TEXT    NOT NULL,
    result      TEXT    NOT NULL,
    mode        TEXT    NOT NULL,
    favorite    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
)
"""


def db_path() -> Path:
    default = Path(__file__).resolve().parent.parent / "data" / "history.db"
    return Path(os.getenv("CONTENTPILOT_DB", default))


@contextmanager
def _conn():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def make_title(kind: str, params: dict) -> str:
    if kind == "topics":
        return params["niche"]
    if kind == "rewrite":
        text = params["text"].strip().replace("\n", " ")
        return text[:24] + ("…" if len(text) > 24 else "")
    return params["topic"]


def make_preview(result: str, limit: int = 80) -> str:
    """生成列表摘要：去掉 Markdown 符号并压成一行。"""
    text = re.sub(r"[#*>`]+", "", result)
    text = re.sub(r"(?m)^\s*[-•]\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _row(r: sqlite3.Row, with_result: bool) -> dict:
    item = {
        "id": r["id"],
        "kind": r["kind"],
        "title": r["title"],
        "mode": r["mode"],
        "favorite": bool(r["favorite"]),
        "created_at": r["created_at"],
    }
    if with_result:
        item["params"] = json.loads(r["params"])
        item["result"] = r["result"]
    else:
        item["preview"] = make_preview(r["result"])
    return item


def add(kind: str, params: dict, result: str, mode: str) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO history (kind, title, params, result, mode, created_at) VALUES (?,?,?,?,?,?)",
            (kind, make_title(kind, params), json.dumps(params, ensure_ascii=False), result, mode, now),
        )
        return cur.lastrowid


def list_items(kind: str | None = None, favorite_only: bool = False, limit: int = 50) -> list[dict]:
    sql, args = "SELECT * FROM history WHERE 1=1", []
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    if favorite_only:
        sql += " AND favorite = 1"
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with _conn() as c:
        return [_row(r, with_result=False) for r in c.execute(sql, args)]


def get(item_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM history WHERE id = ?", (item_id,)).fetchone()
        return _row(r, with_result=True) if r else None


def toggle_favorite(item_id: int) -> bool | None:
    """切换收藏状态，返回切换后的状态；记录不存在返回 None。"""
    with _conn() as c:
        r = c.execute("SELECT favorite FROM history WHERE id = ?", (item_id,)).fetchone()
        if not r:
            return None
        new = 0 if r["favorite"] else 1
        c.execute("UPDATE history SET favorite = ? WHERE id = ?", (new, item_id))
        return bool(new)


def delete(item_id: int) -> bool:
    with _conn() as c:
        return c.execute("DELETE FROM history WHERE id = ?", (item_id,)).rowcount > 0


def clear_unfavorited() -> int:
    """清空所有未收藏的记录，返回删除条数。收藏的记录会保留。"""
    with _conn() as c:
        return c.execute("DELETE FROM history WHERE favorite = 0").rowcount
