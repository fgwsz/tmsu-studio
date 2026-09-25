"""异步分面加载器：把分面计算放到工作线程，避免阻塞 UI。

分两批：
  - 快速批：类型 + 年份（只看路径，毫秒级）
  - 慢速批：标签（对每个文件调 tmsu tags）
快速批先返回，慢速批后返回，UI 渐进式更新。
"""
from collections import Counter
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from .config import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from .facets import YEAR_RE, _type_step
from .query_chain import QueryStep


class _Signals(QObject):
    fastReady = pyqtSignal(int, list)     # (token, [facets...])
    slowReady = pyqtSignal(int, list)     # (token, [facets...])
    failed = pyqtSignal(int)


class _FastTask(QRunnable):
    """只算类型和年份，不碰 tmsu。"""

    def __init__(self, token: int, paths: list[str], signals: _Signals):
        super().__init__()
        self.token = token
        self.paths = paths
        self.signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            facets = _compute_fast(self.paths)
        except Exception:
            facets = []
        self.signals.fastReady.emit(self.token, facets)


class _SlowTask(QRunnable):
    """算标签分面，需要调 tmsu tags。"""

    def __init__(self, token: int, paths: list[str], tmsu, top_n: int,
                 signals: _Signals):
        super().__init__()
        self.token = token
        self.paths = paths
        self.tmsu = tmsu
        self.top_n = top_n
        self.signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            facets = _compute_tags(self.paths, self.tmsu, self.top_n)
        except Exception:
            facets = []
        self.signals.slowReady.emit(self.token, facets)


class FacetLoader(QObject):
    """分面异步调度器。

    用法：
        loader = FacetLoader(tmsu_client)
        loader.facetsReady.connect(on_ready)     # (token, [facets])
        token = loader.request(paths)
    """

    facetsReady = pyqtSignal(int, list)   # 每次批次到达都发一次

    def __init__(self, tmsu_client, parent=None):
        super().__init__(parent)
        self.tmsu = tmsu_client
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self._token = 0
        self._signals = _Signals()
        self._signals.fastReady.connect(self._on_fast)
        self._signals.slowReady.connect(self._on_slow)
        self._signals.failed.connect(lambda t: None)

    def set_tmsu_client(self, client) -> None:
        self.tmsu = client

    def request(self, paths: list[str]) -> int:
        """提交分面计算，返回 token。结果通过 facetsReady 分两批到达。"""
        self._token += 1
        token = self._token
        if not paths:
            return token

        self.pool.start(_FastTask(token, paths, self._signals))
        self.pool.start(_SlowTask(token, paths, self.tmsu, 15, self._signals))
        return token

    def _on_fast(self, token: int, facets: list) -> None:
        self.facetsReady.emit(token, facets)

    def _on_slow(self, token: int, facets: list) -> None:
        self.facetsReady.emit(token, facets)

    def shutdown(self) -> None:
        self.pool.clear()
        self.pool.waitForDone(3000)


# ---------- 计算函数 ----------

def _compute_fast(paths: list[str]) -> list[tuple[str, list]]:
    """类型 + 年份。返回 [(维度名, [(label, n, step), ...]), ...]"""
    result = []

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
    if type_counter:
        steps = []
        for name, n in type_counter.most_common():
            step = _type_step(name)
            if step:
                steps.append((f"{name} ({n})", n, step))
        if steps:
            result.append(("类型", steps))

    year_counter: Counter = Counter()
    for p in paths:
        for part in Path(p).parts:
            if YEAR_RE.match(part):
                year_counter[part] += 1
                break
    if year_counter:
        steps = [
            (f"{y} ({n})", n, QueryStep(
                kind="client",
                label=f"路径含 {y}",
                filter_id=f"year_{y}",
                predicate=(lambda p, yy=y: yy in Path(p).parts),
            ))
            for y, n in sorted(year_counter.items(), reverse=True)[:15]
        ]
        result.append(("年份", steps))

    return result


def _compute_tags(paths: list[str], tmsu, top_n: int) -> list[tuple[str, list]]:
    """标签分面。"""
    tag_counter: Counter = Counter()
    for p in paths:
        for t in tmsu.tags(p):
            tag_counter[t] += 1
    if not tag_counter:
        return []
    steps = [
        (f"{t} ({n})", n, QueryStep(kind="tmsu", expr=t, label=t))
        for t, n in tag_counter.most_common(top_n)
    ]
    return [("标签", steps)]
