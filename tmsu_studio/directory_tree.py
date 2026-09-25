"""目录树：纯导航，不做任何标签操作。状态可持久化，属于界面配置。"""
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem


class DirectoryTree(QTreeWidget):
    dirSelected = pyqtSignal(str)  # 绝对路径

    def __init__(self, root: Path, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.root = Path(root).resolve()
        self.itemClicked.connect(self._on_clicked)
        self._build()

    # ---------- 构建 ----------
    def _build(self) -> None:
        self.clear()
        root_item = QTreeWidgetItem([self.root.name or str(self.root)])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(self.root))
        self.addTopLevelItem(root_item)
        self._load_children(root_item)

    def rebuild(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self._build()

    def _load_children(self, item: QTreeWidgetItem) -> None:
        if item.childCount() > 0:
            return
        path = Path(item.data(0, Qt.ItemDataRole.UserRole))
        try:
            children = sorted(
                (p for p in path.iterdir()
                 if p.is_dir() and not p.name.startswith(".")),
                key=lambda p: p.name.lower(),
            )
        except (OSError, PermissionError):
            return
        for p in children:
            child = QTreeWidgetItem([p.name])
            child.setData(0, Qt.ItemDataRole.UserRole, str(p))
            item.addChild(child)

    # ---------- 鼠标 ----------
    def _on_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        self._load_children(item)
        item.setExpanded(True)
        self.dirSelected.emit(item.data(0, Qt.ItemDataRole.UserRole))

    # ---------- 键盘 ----------
    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item is not None:
                self._load_children(item)
                expanded = not item.isExpanded()
                item.setExpanded(expanded)
                # 只在展开时通知主窗口刷新浏览列表
                if expanded:
                    self.dirSelected.emit(
                        item.data(0, Qt.ItemDataRole.UserRole)
                    )
                return
        super().keyPressEvent(event)

    # ---------- 状态保存/恢复 ----------
    def _rel(self, item: QTreeWidgetItem) -> str:
        p = Path(item.data(0, Qt.ItemDataRole.UserRole))
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return ""

    def save_state(self) -> dict:
        expanded: list[str] = []

        def walk(item: QTreeWidgetItem) -> None:
            if item.isExpanded():
                rel = self._rel(item)
                if rel:
                    expanded.append(rel)
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(self.topLevelItemCount()):
            walk(self.topLevelItem(i))
        return {"expanded": expanded}

    def apply_state(self, state: dict) -> None:
        expanded = set(state.get("expanded", []))
        if not expanded:
            return

        def walk(item: QTreeWidgetItem) -> None:
            rel = self._rel(item)
            if rel == "" or rel in expanded:
                self._load_children(item)
                if rel:
                    item.setExpanded(True)
                for i in range(item.childCount()):
                    walk(item.child(i))

        for i in range(self.topLevelItemCount()):
            walk(self.topLevelItem(i))
