"""图表列表（v3.2）：显示当前项目下的图表，支持编辑/删除/复制。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu


class ChartListWidget(QListWidget):
    chartActivated = Signal(object)   # Chart（双击/点击编辑）
    deleteRequested = Signal(object)  # Chart
    copyRequested = Signal(object)    # Chart（右键复制）

    ROLE_CHART = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemDoubleClicked.connect(self._on_double)
        self.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: 1px solid #d0d0d0;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:selected {
                background: #e3f0ff;
                color: #1a1a1a;
                border-left: 3px solid #1976d2;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background: #f0f7ff;
            }
        """)

    def set_charts(self, charts, sel_chart=None):
        self.clear()
        for c in charts:
            n = len(c.series_list)
            item = QListWidgetItem(f"{c.chart_name}\n{n} 个系列 · X/Y 可编辑")
            item.setData(self.ROLE_CHART, c)
            if sel_chart is not None and sel_chart.id == c.id:
                item.setSelected(True)
            self.addItem(item)

    def _on_double(self, item):
        c = item.data(self.ROLE_CHART)
        if c is not None:
            self.chartActivated.emit(c)

    def selected_chart(self):
        items = self.selectedItems()
        return items[0].data(self.ROLE_CHART) if items else None

    # ---------- 右键菜单 ----------
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            return
        chart = item.data(self.ROLE_CHART)
        if chart is None:
            return
        menu = QMenu(self)
        copy_act = QAction("📋 复制图表", self)
        copy_act.triggered.connect(lambda: self.copyRequested.emit(chart))
        menu.addAction(copy_act)
        menu.exec(event.globalPos())
