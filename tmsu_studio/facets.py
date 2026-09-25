"""对当前结果集计算分面，生成可追加的查询步骤。"""
import re
from collections import Counter
from pathlib import Path

from .config import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from .query_chain import QueryStep


YEAR_RE = re.compile(r"^(19|20)\d{2}$")


def compute(paths: list[str], tmsu_client, top_n: int = 15) -> dict:
    if not paths:
        return {}
    facets: dict[str, list] = {}

    # 1. 标签分面
    tag_counter: Counter = Counter()
    for p in paths:
        for t in tmsu_client.tags(p):
            tag_counter[t] += 1
    if len(tag_counter) >= 2:
        facets["标签"] = [
            (f"{t} ({n})", n, QueryStep(
                kind="tmsu", expr=t, label=t,
            ))
            for t, n in tag_counter.most_common(top_n)
        ]

    # 2. 类型分面
    type_counter: Counter = Counter()
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext in VIDEO_EXT:
            type_counter["视频"] += 1
        elif ext in IMAGE_EXT:
            type_counter["图片"] += 1
        elif ext in AUDIO_EXT:
            type_counter["音频"] += 1
        else:
            type_counter["其他"] += 1
    if len(type_counter) >= 2:
        steps = []
        for name, n in type_counter.most_common():
            step = _type_step(name)
            if step:
                steps.append((f"{name} ({n})", n, step))
        if steps:
            facets["类型"] = steps

    # 3. 年份分面（路径中出现 4 位年份）
    year_counter: Counter = Counter()
    for p in paths:
        for part in Path(p).parts:
            if YEAR_RE.match(part):
                year_counter[part] += 1
                break
    if len(year_counter) >= 2:
        facets["年份"] = [
            (f"{y} ({n})", n, QueryStep(
                kind="client",
                label=f"路径含 {y}",
                filter_id=f"year_{y}",
                predicate=(lambda p, yy=y: yy in Path(p).parts),
            ))
            for y, n in sorted(year_counter.items(), reverse=True)[:top_n]
        ]

    return facets


def _type_step(name: str) -> QueryStep | None:
    if name == "视频":
        return QueryStep(kind="client", label="类型:视频",
                         filter_id="ext_video",
                         predicate=lambda p: Path(p).suffix.lower() in VIDEO_EXT)
    if name == "图片":
        return QueryStep(kind="client", label="类型:图片",
                         filter_id="ext_image",
                         predicate=lambda p: Path(p).suffix.lower() in IMAGE_EXT)
    if name == "音频":
        return QueryStep(kind="client", label="类型:音频",
                         filter_id="ext_audio",
                         predicate=lambda p: Path(p).suffix.lower() in AUDIO_EXT)
    return None
