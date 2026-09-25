"""文件列表：多选 + 拖拽（只复制，不移动）+ 回车打开。"""
from pathlib import Path

from PyQt6.QtCore import Qt, QMimeData, QUrl, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem


class FileListWidget(QListWidget):
    itemActivated = pyqtSignal(QListWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.itemDoubleClicked.connect(self.itemActivated.emit)

    def mimeData(self, items):
        """拖拽时只传原始文件绝对路径，不传目录。"""
        mime = QMimeData()
        mime.setUrls([
            QUrl.fromLocalFile(i.data(Qt.ItemDataRole.UserRole))
            for i in items
        ])
        return mime

    # ---------- 键盘 ----------
    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            items = self.selectedItems()
            if items:
                self.itemActivated.emit(items[0])
                return
        super().keyPressEvent(event)

    # ---------- 数据 ----------
    def add_file(self, abs_path: str, label: str | None = None) -> None:
        it = QListWidgetItem(label or Path(abs_path).name)
        it.setData(Qt.ItemDataRole.UserRole, abs_path)
        self.addItem(it)

    def selected_files(self) -> list[str]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self.selectedItems()]
