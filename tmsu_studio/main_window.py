"""主窗口：Facade 组装目录树、智能集合、查询链、分面、列表、预览。"""
import subprocess
from pathlib import Path

from PyQt6.QtCore import QMimeData, Qt, QUrl, QStringListModel
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QCompleter, QFileDialog, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from . import state
from .collections_panel import CollectionsPanel
from .config import APP_NAME, FACET_LIMIT, is_valid_db, resolve_root
from .directory_tree import DirectoryTree
from .facets_async import FacetLoader
from .file_list import FileListWidget
from .preview import PreviewPanel
from .query_chain import QueryChain, QueryStep
from .tag_input import TagInputDialog, WordCompleter
from .tag_manager import TagManagerDialog
from .thumbnail import ThumbnailCache
from .tmsu_client import TmsuClient, available as tmsu_available


class MainWindow(QMainWindow):
    def __init__(self, root: Path | None = None):
        super().__init__()
        if not tmsu_available():
            QMessageBox.critical(None, "缺少 TMSU",
                                 "未检测到 tmsu 命令，请先安装。")
            raise SystemExit(1)

        self.root = Path(root or resolve_root()).resolve()
        self.scope = self.root
        self.chain = QueryChain()
        self.tmsu = TmsuClient(self.root)
        self.thumb_cache = ThumbnailCache()

        # 分面异步加载器
        self.facet_loader = FacetLoader(self.tmsu, parent=self)
        self.facet_loader.facetsReady.connect(self._on_facets_ready)
        self._current_facet_token = 0
        self._facet_built: set[str] = set()
        self._facet_first_arrival: bool = False

        self.resize(1280, 800)
        self._build_ui()
        self._wire_events()
        self._load_state()

        state.push_recent_db(self.root)
        self._reload_db_combo()
        self._update_title()
        self._reload_tags()
        self._refresh_all()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)

        # 顶部：数据库切换
        top = QHBoxLayout()
        top.addWidget(QLabel("数据库:"))
        self.db_combo = QComboBox()
        self.db_combo.setMinimumWidth(320)
        top.addWidget(self.db_combo)
        self.btn_switch_db = QPushButton("切换…")
        top.addWidget(self.btn_switch_db)
        top.addStretch()
        self.btn_tags = QPushButton("标签管理")
        top.addWidget(self.btn_tags)
        root_lay.addLayout(top)

        # 主体
        main_split = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：智能集合 + 目录树
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(2)

        lbl_coll = QLabel("智能集合")
        lbl_coll.setStyleSheet("padding: 2px 6px; color: #888;")
        left_lay.addWidget(lbl_coll)

        self.collections = CollectionsPanel(self.root)
        self.collections.setMaximumHeight(200)
        left_lay.addWidget(self.collections)

        lbl_tree = QLabel("目录")
        lbl_tree.setStyleSheet("padding: 2px 6px; color: #888;")
        left_lay.addWidget(lbl_tree)

        self.tree = DirectoryTree(self.root)
        left_lay.addWidget(self.tree, 1)

        main_split.addWidget(left)

        # 右侧
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)

        # 查询行
        qrow = QHBoxLayout()
        self.query = QLineEdit()
        self._completer = WordCompleter([], self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.query.setCompleter(self._completer)
        self.query.setPlaceholderText(
            "输入标签查询，例如：music and year>=2020"
        )
        qrow.addWidget(self.query, 1)

        self.btn_run = QPushButton("执行")
        qrow.addWidget(self.btn_run)
        self.btn_reset = QPushButton("重置")
        qrow.addWidget(self.btn_reset)
        self.btn_save_coll = QPushButton("存为集合")
        qrow.addWidget(self.btn_save_coll)
        right_lay.addLayout(qrow)

        # 面包屑
        self.breadcrumb_container = QWidget()
        self.breadcrumb_lay = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.addWidget(self.breadcrumb_container)

        # 中部：文件列表 + 预览
        mid = QSplitter(Qt.Orientation.Horizontal)
        self.file_list = FileListWidget()
        self.file_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        mid.addWidget(self.file_list)

        self.preview = PreviewPanel(self.thumb_cache, self.tmsu)
        mid.addWidget(self.preview)
        mid.setSizes([520, 420])
        mid.setMinimumHeight(240)
        right_lay.addWidget(mid, 1)

        # 分面
        self.facet_scroll = QScrollArea()
        self.facet_scroll.setWidgetResizable(True)
        self.facet_scroll.setMinimumHeight(80)
        self.facet_scroll.setMaximumHeight(120)
        self.facet_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self.facet_container = QWidget()
        self.facet_lay = QVBoxLayout(self.facet_container)
        self.facet_lay.setContentsMargins(4, 0, 4, 0)   # ← 上下边距归零
        self.facet_lay.setSpacing(0)                     # ← 行间距归零
        self.facet_scroll.setWidget(self.facet_container)

        right_lay.addWidget(self.facet_scroll)

        main_split.addWidget(right)
        main_split.setSizes([240, 1040])
        root_lay.addWidget(main_split, 1)

        # 状态栏
        self.statusBar().showMessage("就绪")

    # ---------- 事件绑定 ----------
    def _wire_events(self) -> None:
        self.db_combo.activated.connect(self._on_db_combo)
        self.btn_switch_db.clicked.connect(self._choose_db)
        self.btn_tags.clicked.connect(self._open_tag_manager)

        self.tree.dirSelected.connect(self._on_dir_selected)

        self.collections.collectionSelected.connect(self._load_collection)
        self.collections.collectionSaveRequested.connect(
            self._save_current_as_collection
        )
        self.collections.collectionUpdateRequested.connect(
            self._update_collection
        )

        self.query.returnPressed.connect(self._on_query_enter)
        self.btn_run.clicked.connect(self._on_query_enter)
        self.btn_reset.clicked.connect(self._reset_query)
        self.btn_save_coll.clicked.connect(self._save_current_as_collection)

        self.file_list.customContextMenuRequested.connect(
            self._on_context_menu
        )
        self.file_list.itemActivated.connect(self._on_item_activated)
        self.file_list.currentItemChanged.connect(self._on_selection_changed)

        QShortcut(QKeySequence("Ctrl+A"), self.file_list,
                  lambda: self.file_list.selectAll())
        QShortcut(QKeySequence("F5"), self, self._refresh_all)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_step)
        QShortcut(QKeySequence("Ctrl+S"), self,
                  self._save_current_as_collection)

    # ---------- 状态 ----------
    def _load_state(self) -> None:
        self.tree.apply_state(state.tree_state(self.root))

    def _save_state(self) -> None:
        state.save_tree_state(self.root, self.tree.save_state())

    def closeEvent(self, ev) -> None:
        self._save_state()
        self.preview.shutdown()
        self.facet_loader.shutdown()
        super().closeEvent(ev)

    # ---------- 数据库切换 ----------
    def _reload_db_combo(self) -> None:
        self.db_combo.blockSignals(True)
        self.db_combo.clear()
        cur = str(self.root)
        dbs = state.recent_dbs()
        if cur not in dbs:
            dbs.insert(0, cur)
        for p in dbs:
            label = f"● {p}" if p == cur else p
            self.db_combo.addItem(label, p)
        idx = self.db_combo.findData(cur)
        if idx >= 0:
            self.db_combo.setCurrentIndex(idx)
        self.db_combo.blockSignals(False)

    def _on_db_combo(self, idx: int) -> None:
        data = self.db_combo.itemData(idx)
        if data:
            self._switch_db(Path(data))

    def _choose_db(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "选择包含 .tmsu 的目录", str(self.root)
        )
        if d:
            self._switch_db(Path(d))

    def _switch_db(self, new_root: Path) -> None:
        new_root = new_root.resolve()
        if new_root == self.root:
            return
        if not is_valid_db(new_root):
            QMessageBox.warning(
                self, "无效数据库",
                f"{new_root} 下没有 .tmsu 目录。\n"
                f"请先在该目录执行：tmsu init"
            )
            self._reload_db_combo()
            return

        self._save_state()

        self.root = new_root
        self.scope = new_root
        self.chain = QueryChain()
        self.tmsu = TmsuClient(self.root)
        self.preview.set_tmsu_client(self.tmsu)
        self.facet_loader.set_tmsu_client(self.tmsu)

        self.tree.rebuild(self.root)
        self.collections.set_root(self.root)

        self.query.clear()
        self._load_state()
        state.push_recent_db(self.root)
        self._reload_db_combo()
        self._update_title()
        self._reload_tags()
        self._refresh_all()
        self.statusBar().showMessage(f"已切换到 {self.root}")

    def _update_title(self) -> None:
        self.setWindowTitle(f"{APP_NAME} — {self.root}")

    # ---------- 目录 ----------
    def _on_dir_selected(self, path: str) -> None:
        self.scope = Path(path)
        self._refresh_all()

    # ---------- 智能集合 ----------
    def _load_collection(self, name: str, chain) -> None:
        self.chain = chain
        self.query.clear()
        self._refresh_all()
        self.statusBar().showMessage(
            f"已加载集合「{name}」 — {len(self.chain.steps)} 步"
        )

    def _save_current_as_collection(self) -> None:
        if self.chain.is_empty():
            QMessageBox.information(
                self, "提示", "当前没有查询链，无法保存。"
            )
            return
        name, ok = QInputDialog.getText(
            self, "保存为智能集合", "集合名称："
        )
        if not ok or not name.strip():
            return
        if self.collections.add_collection(name.strip(), self.chain):
            self.statusBar().showMessage(f"已保存集合「{name.strip()}」")

    def _update_collection(self, name: str) -> None:
        if self.chain.is_empty():
            QMessageBox.information(
                self, "提示", "当前没有查询链，无法更新。"
            )
            return
        if QMessageBox.question(
            self, "确认", f"用当前查询链覆盖集合「{name}」？"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.collections.update_collection(name, self.chain)
        self.statusBar().showMessage(f"已更新集合「{name}」")

    # ---------- 查询 ----------
    def _on_query_enter(self) -> None:
        text = self.query.text().strip()
        if not text:
            return
        step = QueryStep(kind="tmsu", expr=text, label=text)
        self.chain = self.chain.push(step)
        state.push_history(self.root, text)
        self.query.clear()
        self._refresh_all()

    def _reset_query(self) -> None:
        self.chain = QueryChain()
        self.query.clear()
        self.scope = self.root
        self._refresh_all()

    def _undo_step(self) -> None:
        if self.chain.is_empty():
            return
        self.chain = self.chain.truncate(len(self.chain.steps) - 1)
        self._refresh_all()

    # ---------- 核心执行 ----------
    def _in_scope(self, path: str) -> bool:
        if self.scope == self.root:
            return True
        try:
            Path(path).resolve().relative_to(self.scope)
            return True
        except ValueError:
            return False

    def _files_in_scope(self) -> list[str]:
        try:
            return [
                str(p) for p in sorted(self.scope.iterdir())
                if p.is_file() and not p.name.startswith(".")
            ]
        except (OSError, PermissionError):
            return []

    def _execute_chain(self) -> list[str]:
        if self.chain.is_empty():
            return self._files_in_scope()

        expr = self.chain.tmsu_expr()
        if expr:
            rel = self.tmsu.files(expr)
            paths = [str(self.tmsu.to_abs(r)) for r in rel]
        else:
            paths = self._files_in_scope()

        for s in self.chain.steps:
            if s.kind == "client":
                paths = s.apply_client(paths)

        return [p for p in paths if self._in_scope(p)]

    def _refresh_all(self) -> None:
        paths = self._execute_chain()
        self._populate_list(paths)
        self._update_breadcrumb()
        self._facet_built = set()
        self._facet_first_arrival = False
        self._update_facets(paths)
        self.statusBar().showMessage(f"{len(paths)} 个文件")

    def _populate_list(self, paths: list[str]) -> None:
        # 1. 记录旧状态
        old_selected = set(self.file_list.selected_files())
        old_current = None
        cur_item = self.file_list.currentItem()
        if cur_item is not None:
            old_current = cur_item.data(Qt.ItemDataRole.UserRole)
        scroll_pos = self.file_list.verticalScrollBar().value()

        # 2. 屏蔽信号，避免 clear 时触发预览清空
        self.file_list.blockSignals(True)
        self.file_list.clear()

        new_current_item = None
        for p in paths:
            try:
                rel = str(Path(p).relative_to(self.root))
            except ValueError:
                rel = p
            self.file_list.add_file(p, rel)
            item = self.file_list.item(self.file_list.count() - 1)
            if p in old_selected:
                item.setSelected(True)
            if p == old_current:
                new_current_item = item

        if new_current_item is not None:
            self.file_list.setCurrentItem(new_current_item)

        self.file_list.blockSignals(False)

        # 3. 恢复滚动位置
        self.file_list.verticalScrollBar().setValue(scroll_pos)

        # 4. 手动触发一次预览（因为信号被屏蔽了）
        cur = self.file_list.currentItem()
        if cur is not None:
            self._on_selection_changed(cur, None)
        else:
            self.preview.show_path("")

    # ---------- 面包屑 ----------
    def _update_breadcrumb(self) -> None:
        while self.breadcrumb_lay.count():
            w = self.breadcrumb_lay.takeAt(0).widget()
            if w:
                w.deleteLater()

        if self.chain.is_empty():
            self.breadcrumb_lay.addWidget(QLabel("(浏览模式)"))
            self.breadcrumb_lay.addStretch()
            return

        for i, step in enumerate(self.chain.steps):
            label = step.label or step.expr or "(空)"
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.clicked.connect(
                lambda _, idx=i: self._jump_to_step(idx + 1)
            )
            self.breadcrumb_lay.addWidget(btn)
            if i < len(self.chain.steps) - 1:
                self.breadcrumb_lay.addWidget(QLabel("›"))

        clear_btn = QPushButton("✕")
        clear_btn.setFixedWidth(28)
        clear_btn.setToolTip("清空查询链")
        clear_btn.clicked.connect(self._reset_query)
        self.breadcrumb_lay.addWidget(clear_btn)
        self.breadcrumb_lay.addStretch()

    def _jump_to_step(self, n: int) -> None:
        self.chain = self.chain.truncate(n)
        self._refresh_all()

    # ---------- 分面（异步） ----------
    def _update_facets(self, paths: list[str]) -> None:
        # 清空旧控件
        while self.facet_lay.count():
            item = self.facet_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        # 无文件 → 隐藏
        if not paths:
            self.facet_scroll.setVisible(False)
            return

        # 结果过多 → 显示提示，不计算
        if len(paths) > FACET_LIMIT:
            self.facet_scroll.setVisible(True)
            self.facet_lay.addWidget(
                QLabel(f"(结果过多：{len(paths)} 个文件，暂不计算分面)")
            )
            return

        self.facet_scroll.setVisible(True)
        self.facet_lay.addWidget(QLabel("计算中…"))

        # 异步提交（快速批 + 慢速批）
        self._current_facet_token = self.facet_loader.request(paths)

    def _on_facets_ready(self, token: int, facets: list) -> None:
        """分面异步结果到达。两批（快、慢）都会触发这个回调。"""
        # 竞态保护：只处理最新一次请求
        if token != self._current_facet_token:
            return

        # 首批到达 → 清空"计算中"占位（不管 facets 是否为空）
        if not self._facet_first_arrival:
            self._facet_first_arrival = True
            while self.facet_lay.count():
                item = self.facet_lay.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

        # 追加新维度（避免第二批重复添加第一批已添加的）
        for name, items in facets:
            if name in self._facet_built:
                continue
            self._facet_built.add(name)
            self._append_facet_row(name, items)

    def _append_facet_row(self, name: str, items: list) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(QLabel(f"<b>{name}</b>"))
        for label, _n, step in items:
            if step is None:
                continue
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setFixedHeight(22)                              # ← 压扁按钮
            btn.setStyleSheet("padding: 0px 6px; text-align: left;")
            btn.clicked.connect(lambda _, s=step: self._apply_facet(s))
            row.addWidget(btn)
        row.addStretch()
        self.facet_lay.addLayout(row)   # ← 直接加 Layout，不再包 QWidget

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _apply_facet(self, step: QueryStep) -> None:
        self.chain = self.chain.push(step)
        self._refresh_all()

    # ---------- 文件操作 ----------
    def _on_selection_changed(self, current, _prev) -> None:
        if current is None:
            self.preview.show_path("")
            return
        self.preview.show_path(
            current.data(Qt.ItemDataRole.UserRole)
        )

    def _on_item_activated(self, item) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        subprocess.Popen(["xdg-open", path])

    def _on_context_menu(self, pos) -> None:
        files = self.file_list.selected_files()
        if not files:
            return

        menu = QMenu(self)
        menu.addAction("添加标签…", lambda: self._tag_op("add"))
        menu.addAction("移除标签…", lambda: self._tag_op("remove"))
        menu.addAction("编辑标签…", lambda: self._tag_op("edit"))
        menu.addSeparator()
        menu.addAction("复制路径", lambda: self._copy_paths(files))
        menu.addAction("打开", lambda: self._open_paths(files))
        menu.addAction("在文件管理器中显示", self._open_dir)
        menu.exec(self.file_list.mapToGlobal(pos))

    def _tag_op(self, mode: str) -> None:
        paths = self.file_list.selected_files()
        if not paths:
            return

        all_tags = self.tmsu.tags()

        if mode == "add":
            text, ok = TagInputDialog.get_text(
                self, "添加标签", "空格分隔多个标签：",
                all_tags, current="",
            )
            if not ok or not text.strip():
                return
            self.tmsu.tag(paths, text.split())

        elif mode == "remove":
            common = self.tmsu.common_tags(paths)
            if not common:
                QMessageBox.information(
                    self, "提示", "选中文件没有共同标签"
                )
                return
            text, ok = TagInputDialog.get_text(
                self, "移除标签", "空格分隔多个标签：",
                all_tags, current=" ".join(sorted(common)),
            )
            if not ok or not text.strip():
                return
            self.tmsu.untag(paths, text.split())

        else:  # edit
            common = self.tmsu.common_tags(paths)
            text, ok = TagInputDialog.get_text(
                self, "编辑标签", "空格分隔多个标签：",
                all_tags, current=" ".join(sorted(common)),
            )
            if not ok:
                return
            new_tags = text.split()
            for p in paths:
                old = self.tmsu.tags(p)
                if old:
                    self.tmsu.untag([p], old)
                if new_tags:
                    self.tmsu.tag([p], new_tags)

        self._reload_tags()
        self._refresh_all()

    def _copy_paths(self, paths: list[str]) -> None:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        mime.setText("\n".join(paths))
        QApplication.clipboard().setMimeData(mime)
        self.statusBar().showMessage(f"已复制 {len(paths)} 条路径")

    def _open_paths(self, paths: list[str]) -> None:
        for p in paths:
            subprocess.Popen(["xdg-open", p])

    def _open_dir(self) -> None:
        files = self.file_list.selected_files()
        if not files:
            return
        subprocess.Popen(["xdg-open", str(Path(files[0]).parent)])

    def _open_tag_manager(self) -> None:
        TagManagerDialog(self.tmsu, self).exec()
        self._reload_tags()
        self._refresh_all()

    # ---------- 补全 ----------
    def _reload_tags(self) -> None:
        tags = self.tmsu.tags()
        self._completer.setModel(QStringListModel(tags, self))
