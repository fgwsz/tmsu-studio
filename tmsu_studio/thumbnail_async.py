"""异步缩略图加载器：用 QThreadPool 把 ffmpeg 放到工作线程。"""
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from .thumbnail import ThumbnailCache


class _TaskSignals(QObject):
    """QRunnable 不能直接有信号，需要一个 QObject 承载。"""
    ready = pyqtSignal(str, str)   # (源路径, 缩略图路径)
    failed = pyqtSignal(str)       # 源路径


class _ThumbnailTask(QRunnable):
    def __init__(self, path: str, cache: ThumbnailCache, signals: _TaskSignals):
        super().__init__()
        self.path = path
        self.cache = cache
        self.signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            result = self.cache.get(self.path)
        except Exception:
            result = None
        if result:
            self.signals.ready.emit(self.path, result)
        else:
            self.signals.failed.emit(self.path)


class ThumbnailLoader(QObject):
    """异步缩略图调度器。

    用法：
        loader = ThumbnailLoader(cache)
        loader.thumbnailReady.connect(on_ready)   # (path, thumb_path)
        loader.thumbnailFailed.connect(on_failed) # (path)
        loader.request("/path/to/video.mp4")
    """

    thumbnailReady = pyqtSignal(str, str)
    thumbnailFailed = pyqtSignal(str)

    def __init__(self, cache: ThumbnailCache, max_threads: int = 2, parent=None):
        super().__init__(parent)
        self.cache = cache
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(max_threads)
        self._pending: set[str] = set()
        self._signals = _TaskSignals()
        self._signals.ready.connect(self._on_ready)
        self._signals.failed.connect(self._on_failed)

    def request(self, path: str) -> None:
        """请求缩略图。缓存命中时同步返回，否则异步生成。"""
        if not path:
            return

        # 快速路径：图片 / 已缓存视频
        if not self.cache.needs_generation(path):
            result = self.cache.get(path)
            if result:
                self.thumbnailReady.emit(path, result)
            else:
                self.thumbnailFailed.emit(path)
            return

        # 去重：同一文件不重复提交
        if path in self._pending:
            return
        self._pending.add(path)

        task = _ThumbnailTask(path, self.cache, self._signals)
        self.pool.start(task)

    def _on_ready(self, path: str, thumb_path: str) -> None:
        self._pending.discard(path)
        self.thumbnailReady.emit(path, thumb_path)

    def _on_failed(self, path: str) -> None:
        self._pending.discard(path)
        self.thumbnailFailed.emit(path)

    def shutdown(self) -> None:
        """程序关闭时调用，等待所有任务结束。"""
        self.pool.clear()
        self.pool.waitForDone(3000)
