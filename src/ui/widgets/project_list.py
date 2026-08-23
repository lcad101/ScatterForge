"""图表列表（v3.2）：显示当前项目下的图表，支持编辑/删除。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class ChartListWidget(QListWidget):
    chartActivated = Signal(object)   # Chart（双击/点击编辑）
    deleteRequested = Signal(object)  # Chart

    ROLE_CHART = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemDoubleClicked.connect(self._on_double)

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
