"""预览面板：异步缩略图 + 路径 + 标签 + 元数据。"""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from .metadata import get_metadata
from .thumbnail import ThumbnailCache
from .thumbnail_async import ThumbnailLoader


class PreviewPanel(QWidget):
    def __init__(self, thumb_cache: ThumbnailCache, tmsu_client, parent=None):
        super().__init__(parent)
        self.thumb_cache = thumb_cache
        self.tmsu = tmsu_client
        self._current_path: str = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.thumb = QLabel("无预览")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setMinimumHeight(160)
        self.thumb.setStyleSheet("background:#1e1e1e; color:#888;")
        lay.addWidget(self.thumb, 1)

        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(160)
        lay.addWidget(self.info)

        # 异步加载器
        self.loader = ThumbnailLoader(thumb_cache, max_threads=2, parent=self)
        self.loader.thumbnailReady.connect(self._on_thumb_ready)
        self.loader.thumbnailFailed.connect(self._on_thumb_failed)

    def set_tmsu_client(self, client) -> None:
        self.tmsu = client

    # ---------- 外部接口 ----------
    def show_path(self, path: str) -> None:
        self._current_path = path
        self.thumb.clear()
        self.thumb.setText("无预览")

        if not path:
            self.info.clear()
            return

        p = Path(path)
        tags = self.tmsu.tags(path)
        meta = get_metadata(p)

        lines = [f"路径：{path}"]
        if tags:
            lines.append(f"标签：{' '.join(tags)}")
        for k, v in meta.items():
            lines.append(f"{k}：{v}")
        self.info.setPlainText("\n".join(lines))

        # 请求缩略图（同步或异步由 loader 决定）
        self.loader.request(path)

    def shutdown(self) -> None:
        self.loader.shutdown()

    # ---------- 回调 ----------
    def _on_thumb_ready(self, path: str, thumb_path: str) -> None:
        # 竞态保护：用户可能已经切到别的文件
        if path != self._current_path:
            return
        pix = QPixmap(thumb_path)
        if pix.isNull():
            return
        w = self.thumb.width() or 480
        h = self.thumb.height() or 320
        self.thumb.setPixmap(pix.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def _on_thumb_failed(self, path: str) -> None:
        if path != self._current_path:
            return
        self.thumb.clear()
        self.thumb.setText("无预览")
