"""项目列表（支持 Ctrl/Shift 多选，冻结规范 2026-08-20 Q2）。

MISSING 项目不可被选中。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class ProjectListView(QListWidget):
    projectActivated = Signal(int)   # 双击 / 回车
    selectionChangedSig = Signal(int)  # 当前选中数量

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.itemDoubleClicked.connect(self._on_double_click)
        self.itemSelectionChanged.connect(self._on_selection)

    def set_projects(self, projects: list) -> None:
        """projects: list[dict(id, name, path, status)]"""
        self.clear()
        for p in projects:
            status_txt = "✅ 正常" if p["status"] == "ACTIVE" else "❌ 缺失"
            text = f"{p['name']}\n{p['path']}\n{status_txt}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, p["status"])
            item.setToolTip(p["path"])
            if p["status"] != "ACTIVE":
                # MISSING 不可选
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                item.setForeground(Qt.GlobalColor.gray)
            self.addItem(item)

    def selected_project_ids(self) -> list[int]:
        return [it.data(Qt.ItemDataRole.UserRole) for it in self.selectedItems()]

    def _on_double_click(self, item) -> None:
        if item.data(Qt.ItemDataRole.UserRole + 1) == "ACTIVE":
            self.projectActivated.emit(item.data(Qt.ItemDataRole.UserRole))

    def _on_selection(self) -> None:
        self.selectionChangedSig.emit(len(self.selectedItems()))
