"""项目树（v3.2）：项目组 → 项目（数据表）→ 图表，三级、可折叠。

- 点击项目组：选中该组（新建项目加到选中的组）。
- 点击项目：选中项目并跳转到数据设置页。
- 点击图表：选中图表并进入系列配置。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem


class ProjectTreeWidget(QTreeWidget):
    groupSelected = Signal(object)     # ProjectGroup
    projectSelected = Signal(object)   # Project
    chartSelected = Signal(object)     # Chart

    ROLE_GROUP = Qt.ItemDataRole.UserRole + 1
    ROLE_PROJECT = Qt.ItemDataRole.UserRole + 2
    ROLE_CHART = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.itemClicked.connect(self._on_click)

    def set_data(self, groups, sel_group=None, sel_project=None, sel_chart=None):
        self.clear()
        for g in groups:
            gitem = QTreeWidgetItem([f"📁 {g.name}"])
            gitem.setData(0, self.ROLE_GROUP, g)
            gitem.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if sel_group is not None and sel_group.id == g.id:
                gitem.setSelected(True)
            for p in g.projects:
                pitem = QTreeWidgetItem([f"📄 {p.name}"])
                pitem.setData(0, self.ROLE_PROJECT, p)
                pitem.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if sel_project is not None and sel_project.id == p.id:
                    pitem.setSelected(True)
                for c in p.charts:
                    citem = QTreeWidgetItem([f"📈 {c.chart_name}"])
                    citem.setData(0, self.ROLE_CHART, c)
                    citem.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    if sel_chart is not None and sel_chart.id == c.id:
                        citem.setSelected(True)
                    pitem.addChild(citem)
                gitem.addChild(pitem)
            self.addTopLevelItem(gitem)

        # 全部加入树后，自顶向下展开，保持展开状态
        for i in range(self.topLevelItemCount()):
            gitem = self.topLevelItem(i)
            gitem.setExpanded(True)
            for j in range(gitem.childCount()):
                gitem.child(j).setExpanded(True)

    def _on_click(self, item, _col):
        g = item.data(0, self.ROLE_GROUP)
        p = item.data(0, self.ROLE_PROJECT)
        c = item.data(0, self.ROLE_CHART)
        if g is not None:
            self.groupSelected.emit(g)
        elif c is not None:
            self.chartSelected.emit(c)
        elif p is not None:
            self.projectSelected.emit(p)
