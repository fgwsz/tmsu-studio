"""UI 状态持久化：最近数据库、目录树展开状态、查询历史、智能集合。

重要：这些是界面状态，不属于数据库。删掉不影响任何标签。
"""
import json
from pathlib import Path
from typing import Any

from .config import STATE_FILE

_DEFAULT = {
    "recent_dbs": [],
    "tree": {},
    "collections": {},
    "history": {},
}


def _load_all() -> dict:
    if not STATE_FILE.exists():
        return {k: (v.copy() if isinstance(v, (list, dict)) else v)
                for k, v in _DEFAULT.items()}
    try:
        data = json.loads(STATE_FILE.read_text())
    except Exception:
        data = {}
    for k, v in _DEFAULT.items():
        data.setdefault(k, [] if isinstance(v, list) else {})
    return data


def _save_all(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ---------- 最近数据库 ----------
def recent_dbs() -> list[str]:
    data = _load_all()
    return [p for p in data["recent_dbs"] if Path(p).is_dir()]


def push_recent_db(root: Path | str) -> None:
    root = str(Path(root).resolve())
    data = _load_all()
    dbs = [p for p in data["recent_dbs"] if Path(p).is_dir() and p != root]
    dbs.insert(0, root)
    data["recent_dbs"] = dbs[:10]
    _save_all(data)


# ---------- 目录树 ----------
def tree_state(root: Path | str) -> dict:
    return _load_all()["tree"].get(str(Path(root).resolve()), {})


def save_tree_state(root: Path | str, state: dict) -> None:
    data = _load_all()
    data["tree"][str(Path(root).resolve())] = state
    _save_all(data)


# ---------- 智能集合 ----------
def collections(root: Path | str) -> list[dict]:
    return _load_all()["collections"].get(str(Path(root).resolve()), [])


def save_collections(root: Path | str, items: list[dict]) -> None:
    data = _load_all()
    data["collections"][str(Path(root).resolve())] = items
    _save_all(data)


# ---------- 查询历史 ----------
def history(root: Path | str) -> list[dict]:
    return _load_all()["history"].get(str(Path(root).resolve()), [])


def push_history(root: Path | str, expr: str) -> None:
    if not expr:
        return
    data = _load_all()
    key = str(Path(root).resolve())
    h = [x for x in data["history"].get(key, []) if x.get("expr") != expr]
    h.insert(0, {"expr": expr})
    data["history"][key] = h[:50]
    _save_all(data)
