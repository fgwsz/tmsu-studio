"""启动对话框：选择或初始化数据库。"""
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

from . import state
from .config import find_db_root_or_none, is_valid_db


class StartupDialog(QDialog):
    """启动时选择/初始化数据库。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TMSU Studio — 选择数据库")
        self.resize(640, 420)
        self._selected: Path | None = None

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("选择一个数据库，或初始化一个新数据库："))

        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        self._reload()

        # 三个入口
        row = QHBoxLayout()
        for label, fn in [
            ("浏览已有数据库…", self._browse),
            ("在当前目录初始化", self._init_cwd),
            ("选择目录并初始化…", self._init_choose),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)

        # 底部按钮
        row2 = QHBoxLayout()
        row2.addStretch()
        b_ok = QPushButton("打开")
        b_ok.setDefault(True)
        b_ok.clicked.connect(self._accept)
        row2.addWidget(b_ok)
        b_cancel = QPushButton("退出")
        b_cancel.clicked.connect(self.reject)
        row2.addWidget(b_cancel)
        lay.addLayout(row2)

        self.list.itemDoubleClicked.connect(lambda _: self._accept())

    # ---------- 列表 ----------
    def _reload(self) -> None:
        self.list.clear()

        # 最近 DB
        for p in state.recent_dbs():
            if is_valid_db(p):
                it = QListWidgetItem(p)
                it.setData(Qt.ItemDataRole.UserRole, p)
                self.list.addItem(it)

        # 当前目录所属 DB 高亮
        cwd = Path.cwd()
        db_root = find_db_root_or_none(cwd)
        if db_root and is_valid_db(db_root):
            for i in range(self.list.count()):
                if self.list.item(i).text() == str(db_root):
                    self.list.setCurrentRow(i)
                    return
            it = QListWidgetItem(f"{db_root}   (当前目录)")
            it.setData(Qt.ItemDataRole.UserRole, str(db_root))
            self.list.insertItem(0, it)
            self.list.setCurrentRow(0)

    # ---------- 操作 ----------
    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择包含 .tmsu 的目录")
        if not d:
            return
        root = find_db_root_or_none(Path(d))
        if not root:
            QMessageBox.warning(
                self, "未找到数据库",
                f"{d}\n及其父目录都没有 .tmsu。\n"
                f"可点击“选择目录并初始化…”新建一个。"
            )
            return
        self._selected = root
        self.accept()

    def _init_cwd(self) -> None:
        self._init_at(Path.cwd())

    def _init_choose(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择要初始化的目录")
        if d:
            self._init_at(Path(d))

    def _init_at(self, d: Path) -> None:
        d = d.resolve()
        if is_valid_db(d):
            QMessageBox.information(self, "已存在", f"{d} 已有 .tmsu。")
            self._selected = d
            self.accept()
            return
        if QMessageBox.question(
            self, "初始化数据库",
            f"将在 {d}\n创建 .tmsu 数据库。继续吗？"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            r = subprocess.run(
                ["tmsu", "init"],
                cwd=str(d),
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0:
                raise RuntimeError((r.stderr or r.stdout).strip())
        except Exception as e:
            QMessageBox.critical(self, "初始化失败", str(e))
            return
        self._selected = d
        state.push_recent_db(d)
        self.accept()

    def _accept(self) -> None:
        it = self.list.currentItem()
        if it is None:
            QMessageBox.information(self, "提示", "请先选择一个数据库。")
            return
        self._selected = Path(it.data(Qt.ItemDataRole.UserRole))
        self.accept()

    def selected_root(self) -> Path | None:
        return self._selected
