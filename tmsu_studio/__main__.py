"""入口：python -m tmsu_studio"""
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog

from . import state
from .config import (
    APP_NAME, APP_VERSION, ensure_dirs,
    find_db_root_or_none, is_valid_db,
)
from .main_window import MainWindow
from .startup import StartupDialog


def _determine_root() -> Path | None:
    """按优先级决定启动时的 DB 根。"""
    # 1. 命令行参数
    for arg in sys.argv[1:]:
        p = Path(arg).expanduser()
        if p.is_dir():
            root = find_db_root_or_none(p)
            if root:
                return root

    # 2. 环境变量
    env = os.environ.get("TMSU_ROOT")
    if env:
        p = Path(env).expanduser()
        if is_valid_db(p):
            return p.resolve()

    # 3. 当前工作目录向上查找
    root = find_db_root_or_none(Path.cwd())
    if root:
        return root

    # 4. 无法自动确定
    return None


def main() -> None:
    ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    root = _determine_root()
    if root is None:
        dlg = StartupDialog()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        root = dlg.selected_root()
        if root is None:
            sys.exit(0)

    state.push_recent_db(root)

    window = MainWindow(root)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
