"""带补全的标签输入对话框。"""
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtWidgets import (
    QCompleter, QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout,
)


class WordCompleter(QCompleter):
    """只对最后一个空格之后的词做补全。"""

    def splitPath(self, path: str) -> list[str]:
        words = path.split()
        return [words[-1]] if words else [""]


class TagInputDialog(QDialog):
    def __init__(self, tags: list[str], current: str = "",
                 title: str = "输入标签",
                 label: str = "空格分隔多个标签：",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(440, 140)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(label))

        self.edit = QLineEdit(current)
        completer = WordCompleter(tags, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.edit.setCompleter(completer)
        lay.addWidget(self.edit)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self.edit.setFocus()
        self.edit.selectAll()

    def value(self) -> str:
        return self.edit.text().strip()

    @classmethod
    def get_text(cls, parent, title: str, label: str,
                 tags: list[str], current: str = "") -> tuple[str, bool]:
        dlg = TagInputDialog(tags, current, title, label, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.value(), True
        return "", False
