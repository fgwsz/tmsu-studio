"""智能集合面板：保存和调用查询链。"""
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QInputDialog, QListWidget, QListWidgetItem, QMenu, QMessageBox,
)

from . import state
from .query_chain import QueryChain


class CollectionsPanel(QListWidget):
    """侧边栏的智能集合列表。

    信号：
        collectionSelected(name, chain)    用户点击某个集合
        collectionSaveRequested()          用户要求保存当前查询为新集合
        collectionUpdateRequested(name)    用户要求用当前查询更新某集合
    """

    collectionSelected = pyqtSignal(str, object)
    collectionSaveRequested = pyqtSignal()
    collectionUpdateRequested = pyqtSignal(str)

    def __init__(self, root: Path, parent=None):
        super().__init__(parent)
        self.root = Path(root).resolve()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_menu)
        self.itemClicked.connect(self._on_clicked)
        self.itemDoubleClicked.connect(self._rename)
        self.reload()

    # ---------- 加载 ----------
    def reload(self) -> None:
        self.clear()
        for c in state.collections(self.root):
            it = QListWidgetItem(f"★ {c['name']}")
            it.setData(Qt.ItemDataRole.UserRole, c)
            self.addItem(it)

    def set_root(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.reload()

    # ---------- 交互 ----------
    def _on_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        chain = QueryChain.from_json(data.get("chain", []))
        self.collectionSelected.emit(data["name"], chain)

    def _on_menu(self, pos) -> None:
        item = self.itemAt(pos)
        menu = QMenu(self)
        if item is None:
            menu.addAction("新建集合…",
                           self.collectionSaveRequested.emit)
        else:
            data = item.data(Qt.ItemDataRole.UserRole)
            menu.addAction("重命名…", lambda: self._rename(item))
            menu.addAction(
                "更新为当前查询",
                lambda: self.collectionUpdateRequested.emit(data["name"]),
            )
            menu.addSeparator()
            menu.addAction("删除", lambda: self._delete(item))
        menu.exec(self.mapToGlobal(pos))

    # ---------- 操作 ----------
    def _rename(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        new, ok = QInputDialog.getText(
            self, "重命名集合", "新名称：", text=data["name"]
        )
        if not ok or not new.strip() or new.strip() == data["name"]:
            return
        items = state.collections(self.root)
        for c in items:
            if c["name"] == data["name"]:
                c["name"] = new.strip()
                break
        state.save_collections(self.root, items)
        self.reload()

    def _delete(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(
            self, "确认", f"删除集合「{data['name']}」？"
        ) != QMessageBox.StandardButton.Yes:
            return
        items = state.collections(self.root)
        items = [c for c in items if c["name"] != data["name"]]
        state.save_collections(self.root, items)
        self.reload()

    # ---------- 主窗口调用的辅助 ----------
    def add_collection(self, name: str, chain: QueryChain) -> bool:
        items = state.collections(self.root)
        if any(c["name"] == name for c in items):
            QMessageBox.warning(self, "重名",
                                f"已存在集合「{name}」。")
            return False
        items.append({"name": name, "chain": chain.to_json()})
        state.save_collections(self.root, items)
        self.reload()
        return True

    def update_collection(self, name: str, chain: QueryChain) -> None:
        items = state.collections(self.root)
        for c in items:
            if c["name"] == name:
                c["chain"] = chain.to_json()
                break
        state.save_collections(self.root, items)
        self.reload()
