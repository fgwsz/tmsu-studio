"""查询链：对结果集逐步叠加条件。"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class QueryStep:
    kind: str = "tmsu"          # "tmsu" | "client"
    expr: str = ""              # TMSU 表达式（kind=tmsu 时有效）
    label: str = ""             # 显示名
    filter_id: str = ""         # 客户端过滤标识（用于序列化）
    predicate: Optional[Callable[[str], bool]] = None  # 不可序列化，运行时重建

    def apply_client(self, paths: list[str]) -> list[str]:
        if self.kind == "client" and self.predicate:
            return [p for p in paths if self.predicate(p)]
        return paths


@dataclass
class QueryChain:
    steps: list[QueryStep] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.steps

    def tmsu_expr(self) -> str:
        return " and ".join(
            s.expr for s in self.steps if s.kind == "tmsu" and s.expr
        )

    def push(self, step: QueryStep) -> "QueryChain":
        return QueryChain(self.steps + [step])

    def truncate(self, n: int) -> "QueryChain":
        return QueryChain(self.steps[:n])

    def to_json(self) -> list[dict]:
        return [
            {"kind": s.kind, "expr": s.expr,
             "label": s.label, "filter_id": s.filter_id}
            for s in self.steps
        ]

    @classmethod
    def from_json(cls, data: list[dict]) -> "QueryChain":
        steps = []
        for d in data:
            pred = CLIENT_FILTERS.get(d.get("filter_id", ""))
            steps.append(QueryStep(
                kind=d.get("kind", "tmsu"),
                expr=d.get("expr", ""),
                label=d.get("label", ""),
                filter_id=d.get("filter_id", ""),
                predicate=pred,
            ))
        return cls(steps)


# ---------- 客户端过滤器注册表 ----------
def _size_mb(p: str) -> float:
    try:
        return Path(p).stat().st_size / 1024 / 1024
    except OSError:
        return 0


def _ext_in(p: str, exts: set[str]) -> bool:
    return Path(p).suffix.lower() in exts


CLIENT_FILTERS: dict[str, Callable[[str], bool]] = {
    "size_gt_100mb": lambda p: _size_mb(p) > 100,
    "size_gt_1gb":   lambda p: _size_mb(p) > 1024,
    "size_lt_10mb":  lambda p: _size_mb(p) < 10,
    "ext_video":     lambda p: _ext_in(p, {".mp4", ".mkv", ".mov",
                                           ".avi", ".webm", ".m4v"}),
    "ext_image":     lambda p: _ext_in(p, {".jpg", ".jpeg", ".png",
                                           ".gif", ".bmp", ".webp"}),
    "ext_audio":     lambda p: _ext_in(p, {".mp3", ".flac", ".wav",
                                           ".aac", ".ogg", ".m4a"}),
    "name_has_drone": lambda p: "drone" in Path(p).name.lower(),
    "name_has_raw":   lambda p: "raw" in Path(p).name.lower(),
}
