"""TMSU 命令行封装（Repository 模式）。

关键约定：TMSU 数据库里存的是相对于数据库根的路径。
所有对外接收绝对路径的接口，内部都要转成相对路径再调用 tmsu。
"""
import subprocess
from pathlib import Path
from typing import Iterable


class TmsuClient:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    # ---------- 内部 ----------
    def _run(self, *args: str, timeout: int = 30) -> str:
        try:
            r = subprocess.run(
                ["tmsu", *args],
                cwd=str(self.root),
                text=True,
                capture_output=True,
                timeout=timeout,
            )
            return r.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def _to_rel(self, path: str | Path) -> str:
        """绝对路径 → 相对数据库根的路径。已在根内则原样返回。"""
        p = Path(path)
        try:
            return str(p.resolve().relative_to(self.root))
        except ValueError:
            return str(path)

    # ---------- 查询 ----------
    def files(self, expr: str) -> list[str]:
        if not expr.strip():
            return []
        return [l.strip() for l in self._run("files", expr).splitlines() if l.strip()]

    def tags(self, path: str | None = None) -> list[str]:
        if path:
            rel = self._to_rel(path)
            out = self._run("tags", rel)
            return self._filter_tags(out, rel, str(path))
        return self._run("tags").split()

    @staticmethod
    def _filter_tags(out: str, *forbidden: str) -> list[str]:
        """过滤 TMSU 对未索引文件的回显。

        可能的输出格式：
          1. 纯标签：      music jazz 2024
          2. 纯回显：      杂项/说唱/day final.mp4:
          3. 路径+标签：   path/file.mp4: music jazz 2024
        策略：
          - 整行以冒号结尾 → 回显，返回空
          - 含 ": " → 取冒号后部分作为标签
          - 否则按空格切
        再逐词过滤掉路径特征。
        """
        out = out.strip()
        if not out:
            return []

        forbidden_set = {str(f).strip() for f in forbidden}

        # 情况 1：整行以冒号结尾 → 纯回显
        if out.endswith(":"):
            return []

        # 情况 3：形如 "路径: 标签1 标签2" → 只取冒号后
        if ": " in out:
            _, _, after = out.partition(": ")
            out = after.strip()

        # 逐词过滤
        result = []
        for raw in out.split():
            t = raw.strip().strip(":")
            if not t:
                continue
            if t in forbidden_set:
                continue
            if t.startswith("/"):
                continue
            if "/" in t:
                continue
            if len(t) >= 2 and t[1] == ":":
                continue
            result.append(t)
        return result

    def common_tags(self, paths: Iterable[str]) -> set[str]:
        sets = [set(self.tags(p)) for p in paths]
        if not sets:
            return set()
        return set.intersection(*sets)

    # ---------- 写入 ----------
    def tag(self, paths: Iterable[str], tags: Iterable[str]) -> None:
        rels = [self._to_rel(p) for p in paths]
        tag_list = list(tags)
        if rels and tag_list:
            self._run("tag", "--tags", " ".join(tag_list), *rels)


    def untag(self, paths: Iterable[str], tags: Iterable[str]) -> None:
        rels = [self._to_rel(p) for p in paths]
        tag_list = list(tags)
        if rels and tag_list:
            self._run("untag", "--tags", " ".join(tag_list), *rels)

    def rename(self, old: str, new: str) -> None:
        self._run("rename", old, new)

    def merge(self, old: str, new: str) -> None:
        self._run("merge", old, new)

    def delete(self, tag: str) -> None:
        self._run("delete", tag)

    def repair(self) -> None:
        self._run("repair")

    # ---------- 工具 ----------
    def to_abs(self, rel: str) -> Path:
        return (self.root / rel).resolve()


def available() -> bool:
    try:
        subprocess.run(["tmsu", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
