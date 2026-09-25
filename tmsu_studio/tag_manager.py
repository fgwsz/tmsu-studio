"""标签管理对话框。"""
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)


class TagManagerDialog(QDialog):
    def __init__(self, tmsu_client, parent=None):
        super().__init__(parent)
        self.tmsu = tmsu_client
        self.setWindowTitle("标签管理")
        self.resize(320, 480)

        lay = QVBoxLayout(self)
        self.list = QListWidget()
        lay.addWidget(self.list)

        row = QHBoxLayout()
        for label, fn in [
            ("重命名", self.rename),
            ("合并", self.merge),
            ("删除", self.delete),
            ("刷新", self.reload),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        self.reload()

    def reload(self) -> None:
        self.list.clear()
        for t in self.tmsu.tags():
            self.list.addItem(QListWidgetItem(t))

    def _current(self) -> str | None:
        it = self.list.currentItem()
        return it.text() if it else None

    def rename(self) -> None:
        old = self._current()
        if not old:
            return
        new, ok = QInputDialog.getText(self, "重命名", "新名称：", text=old)
        if ok and new and new != old:
            self.tmsu.rename(old, new)
            self.reload()

    def merge(self) -> None:
        old = self._current()
        if not old:
            return
        new, ok = QInputDialog.getText(self, "合并到", "目标标签：")
        if ok and new:
            self.tmsu.merge(old, new)
            self.reload()

    def delete(self) -> None:
        t = self._current()
        if not t:
            return
        if QMessageBox.question(self, "确认", f"删除标签 {t}？") == \
                QMessageBox.StandardButton.Yes:
            self.tmsu.delete(t)
            self.reload()
