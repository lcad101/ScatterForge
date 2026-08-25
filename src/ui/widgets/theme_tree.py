"""项目树（v3.2）：项目组 → 项目（数据表）→ 图表，三级、可折叠。

- 点击项目组：选中该组（新建项目加到选中的组）。
- 点击项目：选中项目并跳转到数据设置页。
- 点击图表：选中图表并跳转到图表预览。
- 右键项目组：弹出菜单可改名。
- 右键项目：弹出菜单可复制/改名。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem


class ProjectTreeWidget(QTreeWidget):
    groupSelected = Signal(object)     # ProjectGroup
    projectSelected = Signal(object)   # Project
    chartSelected = Signal(object)     # Chart
    copyProjectRequested = Signal(object)  # Project（右键复制项目）
    renameGroupRequested = Signal(object)   # ProjectGroup（右键改名）
    renameProjectRequested = Signal(object)  # Project（右键改名）

    ROLE_GROUP = Qt.ItemDataRole.UserRole + 1
    ROLE_PROJECT = Qt.ItemDataRole.UserRole + 2
    ROLE_CHART = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.itemClicked.connect(self._on_click)
        self.setStyleSheet("""
            QTreeWidget {
                background: #ffffff;
                border: 1px solid #d0d0d0;
            }
            QTreeWidget::item {
                padding: 4px 6px;
                border-left: 3px solid transparent;
            }
            QTreeWidget::item:selected {
                background: #e3f0ff;
                color: #1a1a1a;
                border-left: 3px solid #1976d2;
                font-weight: bold;
            }
            QTreeWidget::item:hover:!selected {
                background: #f0f7ff;
            }
        """)

    def set_data(self, groups, sel_group=None, sel_project=None, sel_chart=None):
        # 保存当前展开状态（用项目 ID 集合记录）
        expanded_projects: set[int] = set()
        for i in range(self.topLevelItemCount()):
            gitem = self.topLevelItem(i)
            if not gitem.isExpanded():
                continue
            for j in range(gitem.childCount()):
                pitem = gitem.child(j)
                if pitem.isExpanded():
                    p = pitem.data(0, self.ROLE_PROJECT)
                    if p is not None:
                        expanded_projects.add(p.id)

        self.clear()
        # ---- 第一阶段：创建节点并加入树（setExpanded 在此阶段无效） ----
        groups_info: list[tuple[QTreeWidgetItem, list[tuple[QTreeWidgetItem, bool]]]] = []
        for g in groups:
            gitem = QTreeWidgetItem([f"📁 {g.name}"])
            gitem.setData(0, self.ROLE_GROUP, g)
            gitem.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if sel_group is not None and sel_group.id == g.id:
                gitem.setSelected(True)
            projects_info: list[tuple[QTreeWidgetItem, bool]] = []
            for p in g.projects:
                pitem = QTreeWidgetItem([f"📄 {p.name}"])
                pitem.setData(0, self.ROLE_PROJECT, p)
                pitem.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                is_selected = sel_project is not None and sel_project.id == p.id
                if is_selected:
                    pitem.setSelected(True)
                for c in p.charts:
                    citem = QTreeWidgetItem([f"📈 {c.chart_name}"])
                    citem.setData(0, self.ROLE_CHART, c)
                    citem.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    if sel_chart is not None and sel_chart.id == c.id:
                        citem.setSelected(True)
                    pitem.addChild(citem)
                gitem.addChild(pitem)
                projects_info.append((pitem, p.id in expanded_projects or is_selected))
            self.addTopLevelItem(gitem)
            groups_info.append((gitem, projects_info))
        # ---- 第二阶段：统一设置展开状态（节点已入树，setExpanded 生效） ----
        for gitem, projects_info in groups_info:
            any_expanded = False
            for pitem, should_expand in projects_info:
                if should_expand:
                    pitem.setExpanded(True)
                    any_expanded = True
            if any_expanded:
                gitem.setExpanded(True)

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

    # ---------- 右键菜单 ----------
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            return
        group = item.data(0, self.ROLE_GROUP)
        project = item.data(0, self.ROLE_PROJECT)
        menu = QMenu(self)
        if group is not None:
            rename_act = QAction("✏️ 改名", self)
            rename_act.triggered.connect(lambda: self.renameGroupRequested.emit(group))
            menu.addAction(rename_act)
        elif project is not None:
            rename_act = QAction("✏️ 改名", self)
            rename_act.triggered.connect(lambda: self.renameProjectRequested.emit(project))
            menu.addAction(rename_act)
            copy_act = QAction("📋 复制项目", self)
            copy_act.triggered.connect(lambda: self.copyProjectRequested.emit(project))
            menu.addAction(copy_act)
        else:
            return  # 图表节点无右键菜单
        menu.exec(event.globalPos())
