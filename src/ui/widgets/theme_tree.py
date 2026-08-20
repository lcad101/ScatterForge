"""主题树（支持拖拽排序，冻结规范 2026-08-20 Q5）。

仅主题（顶层）可拖拽排序，项目不可跨主题移动/拖拽。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem


class DragDropThemeTree(QTreeWidget):
    orderChanged = Signal()  # 主题顺序变化后发出

    THEME_ROLE = Qt.ItemDataRole.UserRole + 1
    PROJECT_ROLE = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

    # ---- 填充数据 ----
    def set_data(self, themes: list, active_theme_id=None):
        self.clear()
        for theme in themes:
            item = QTreeWidgetItem([f"📁 {theme['name']}"])
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
            item.setData(0, self.THEME_ROLE, theme["id"])
            item.setExpanded(True)
            if theme["id"] == active_theme_id:
                item.setSelected(True)
            for p in theme.get("projects", []):
                child = QTreeWidgetItem([f"{'🟢' if p['status'] == 'ACTIVE' else '🔴'} {p['name']}"])
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)  # 项目不可拖拽
                child.setData(0, self.PROJECT_ROLE, p["id"])
                item.addChild(child)
            self.addTopLevelItem(item)

    # ---- 拖拽完成 → 发出顺序变化 ----
    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.orderChanged.emit()

    # ---- 读取当前主题 id 顺序 ----
    def theme_order(self) -> list[int]:
        return [self.topLevelItem(i).data(0, self.THEME_ROLE) for i in range(self.topLevelItemCount())]
