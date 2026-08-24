"""主窗口（v3.2）：项目组→项目→图表→系列 三级管理 + 精确行列范围 + 多图多 Sheet 导出。"""
from __future__ import annotations

import os
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTabWidget,
    QVBoxLayout, QWidget,
)

from src.core.database import SessionLocal
from src.core.exceptions import OperationCancelledException
from src.models import ACTIVE, MISSING, Chart, ChartLimit, Project, ProjectGroup, Series
from src.services.chart_builder import ChartOptions, LimitRule, SeriesConfig
from src.services.excel_export_service import ChartSpec, ExcelExportService
from src.services.excel_handler import RAW_DATA_SHEET, ExcelHandler, SheetSlice
from src.services.file_probe_service import FileProbeService
from src.ui.dialogs import ExportDialog, default_export_name
from src.ui.views import ImportView, OptionsView, SeriesView
from src.ui.widgets import ChartListWidget, PreviewWidget, ProjectTreeWidget

DEFAULT_GROUP = "默认项目组"


class ImportWorker(QThread):
    success = Signal(object)   # SheetSlice
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, path, start_row, end_row, start_col, end_col, read_raw=False, parent=None):
        super().__init__(parent)
        self._handler = ExcelHandler()
        self._args = (path, start_row, end_row, start_col, end_col)
        self._read_raw = read_raw

    def cancel(self):
        self._handler.cancel()

    def run(self):
        try:
            path, sr, er, sc, ec = self._args
            sl = self._handler.read_range(path, sr, er, sc, ec,
                                          sheet=RAW_DATA_SHEET if self._read_raw else None)
            self.success.emit(sl)
        except OperationCancelledException:
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ProbeWorker(QThread):
    done = Signal()
    failed = Signal(str)

    def run(self):
        session = SessionLocal()
        try:
            FileProbeService().probe(session)
            self.done.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            session.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Excel 散点图生成器 — ScatterForge")
        self.resize(1280, 800)

        self.db = SessionLocal()
        self.current_group: ProjectGroup | None = None
        self.current_project: Project | None = None
        self.current_chart: Chart | None = None
        self.source_slice: SheetSlice | None = None
        self.source_name: str = ""
        self._import_worker: ImportWorker | None = None

        self._build_ui()
        self._refresh_all()
        self._probe_async()

    # ================= UI =================
    def _build_ui(self):
        # 左：项目树
        self.tree = ProjectTreeWidget()
        self.tree.groupSelected.connect(self._on_group_selected)
        self.tree.projectSelected.connect(self._on_project_selected)
        self.tree.chartSelected.connect(self._on_chart_selected)
        self.tree.copyProjectRequested.connect(self._copy_project)

        add_project_btn = QPushButton("＋项目")
        add_project_btn.setToolTip("在选中的项目组下新建项目（数据表）")
        add_project_btn.clicked.connect(self._add_project)
        add_group_btn = QPushButton("＋项目组")
        add_group_btn.clicked.connect(self._add_group)
        del_group_btn = QPushButton("🗑 项目组")
        del_group_btn.clicked.connect(self._delete_group)
        del_project_btn = QPushButton("🗑 项目")
        del_project_btn.clicked.connect(self._delete_project)
        btns = QVBoxLayout()
        row1 = _hbox([add_project_btn, add_group_btn])
        row2 = _hbox([del_group_btn, del_project_btn])
        btns.addLayout(row1)
        btns.addLayout(row2)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)
        ll.addWidget(QLabel("📁 项目组"))
        ll.addWidget(self.tree, 1)
        ll.addLayout(btns)

        # 中：图表列表
        self.chart_list = ChartListWidget()
        self.chart_list.chartActivated.connect(self._on_chart_selected)
        self.chart_list.copyRequested.connect(self._copy_chart)
        add_chart_btn = QPushButton("＋新建图表")
        add_chart_btn.clicked.connect(self._add_chart)
        copy_chart_btn = QPushButton("📋 复制图表")
        copy_chart_btn.setToolTip("复制当前选中的图表（含全部系列和设置）")
        copy_chart_btn.clicked.connect(self._copy_chart)
        del_chart_btn = QPushButton("🗑 删除图表")
        del_chart_btn.clicked.connect(self._delete_chart)
        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(4, 4, 4, 4)
        ml.addWidget(QLabel("📋 图表"))
        ml.addWidget(self.chart_list, 1)
        ml.addLayout(_hbox([add_chart_btn, copy_chart_btn, del_chart_btn]))

        # 右：标签页
        self.tabs = QTabWidget()
        self.start_page = self._build_start_page()
        self.import_view = ImportView()
        self.import_view.applyRequested.connect(self._import)
        self.series_view = SeriesView()
        self.series_view.changed.connect(self._preview)
        self.options_view = OptionsView()
        self.options_view.changed.connect(self._preview)
        self.preview = PreviewWidget()

        self.tabs.addTab(self.start_page, "开始")
        self.tabs.addTab(self.import_view, "数据设置")
        self.tabs.addTab(self.series_view, "系列配置")
        self.tabs.addTab(self.options_view, "图表选项")
        self.tabs.addTab(self.preview, "图表预览")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(mid)
        splitter.addWidget(self.tabs)
        splitter.setSizes([260, 300, 720])
        self.setCentralWidget(splitter)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("导入原始数据…", lambda: self.tabs.setCurrentWidget(self.import_view))
        file_menu.addAction("导出散点图文件…", self._export)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        tb = self.addToolBar("主工具栏")
        tb.setMovable(False)
        tb.addAction("📥 导入原始数据", lambda: self.tabs.setCurrentWidget(self.import_view))
        tb.addAction("📈 导出散点图文件", self._export)
        tb.addAction("🔄 刷新状态", self._probe_async)

        self.statusBar().showMessage("就绪")

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("📊 最近打开的项目"))
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._on_recent_clicked)
        layout.addWidget(self.recent_list, 1)
        imp = QPushButton("📂 导入新数据")
        imp.clicked.connect(lambda: self.tabs.setCurrentWidget(self.import_view))
        layout.addWidget(imp)
        return page

    # ================= 刷新 =================
    def _groups(self):
        return self.db.query(ProjectGroup).order_by(ProjectGroup.sort_order, ProjectGroup.id).all()

    def _refresh_all(self):
        # 过期全部对象，确保树/列表读到最新关系（新增图表/系列后集合同步）
        self.db.expire_all()
        self._refresh_tree()
        self._refresh_chart_list()
        self._refresh_recent()

    def _refresh_tree(self):
        self.tree.set_data(self._groups(), self.current_group, self.current_project, self.current_chart)

    def _refresh_chart_list(self):
        charts = self.current_project.charts if self.current_project else []
        self.chart_list.set_charts(charts, self.current_chart)

    def _refresh_recent(self):
        self.recent_list.clear()
        recent = (self.db.query(Project)
                  .filter(Project.last_opened_at.isnot(None))
                  .order_by(Project.last_opened_at.desc()).limit(5).all())
        for p in recent:
            mark = "❌ " if p.status == MISSING else ""
            item = QListWidgetItem(f"{mark}{p.name}\n{p.source_file_path}")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.recent_list.addItem(item)

    def _columns(self) -> list[tuple[str, str]]:
        if not self.source_slice:
            return [("A", "A"), ("B", "B")]
        return list(zip(self.source_slice.column_letters, self.source_slice.headers))

    # ================= 选择事件 =================
    def _on_group_selected(self, group: ProjectGroup):
        self.current_group = group
        self._refresh_tree()

    def _on_project_selected(self, project: Project):
        self._sync_current_chart()
        self.current_project = project
        self.current_chart = project.charts[0] if project.charts else None
        self.current_group = project.group
        project.last_opened_at = datetime.now()
        if not os.path.isfile(project.source_file_path):
            project.status = MISSING
            self.db.commit()
            self._refresh_all()
            QMessageBox.warning(self, "文件缺失",
                                f"项目「{project.name}」的导出文件不存在。\n请在数据设置页重新导入原始数据。")
            self.tabs.setCurrentWidget(self.import_view)
            return
        project.status = ACTIVE
        self.db.commit()
        self._refresh_all()
        # 从导出文件的 raw data 页重新读取
        self._run_import(project.source_file_path, project.data_start_row, project.data_end_row,
                         project.data_start_col_letter, project.data_end_col_letter, read_raw=True)
        self.tabs.setCurrentWidget(self.import_view)

    def _on_chart_selected(self, chart: Chart):
        self._sync_current_chart()
        self.current_chart = chart
        self._load_chart(chart)
        self._refresh_tree()
        self._refresh_chart_list()
        self.tabs.setCurrentWidget(self.series_view)

    # ================= 图表状态 =================
    def _load_chart(self, chart: Chart):
        series = [SeriesConfig(name=s.series_name, x_col=s.x_col_letter, y_col=s.y_col_letter,
                               row_start=s.row_start, row_end=s.row_end, color=s.color_hex,
                               shape=s.marker_shape, size=s.marker_size) for s in chart.series_list]
        self.series_view.set_series(series, self._columns())
        self.options_view.set_columns(self._columns())
        opts = ChartOptions(
            title=chart.chart_title, x_label=chart.x_axis_label, y_label=chart.y_axis_label,
            x_min=chart.x_axis_min, x_max=chart.x_axis_max, y_min=chart.y_axis_min, y_max=chart.y_axis_max,
            x_major_unit=chart.x_axis_major_unit, x_minor_unit=chart.x_axis_minor_unit,
            y_major_unit=chart.y_axis_major_unit, y_minor_unit=chart.y_axis_minor_unit,
            show_grid=chart.show_grid, connect_line=chart.connect_line,
            rules=[LimitRule(x_col=l.x_col_letter, y_col=l.y_col_letter,
                             x_start=l.x_start, x_end=l.x_end, y_min=l.y_min, y_max=l.y_max)
                   for l in chart.limits])
        self.options_view.set_options(opts)
        self.options_view.chart_name.setText(chart.chart_name)
        self._preview()

    def _sync_current_chart(self):
        """把当前图表视图中的系列/选项写回 DB（切换/导出前调用）。"""
        if not self.current_chart or not self.current_project:
            return
        chart = self.current_chart
        chart.chart_name = self.options_view.get_chart_name()
        opts = self.options_view.get_options()
        chart.chart_title = opts.title
        chart.x_axis_label = opts.x_label
        chart.y_axis_label = opts.y_label
        chart.x_axis_min = opts.x_min
        chart.x_axis_max = opts.x_max
        chart.y_axis_min = opts.y_min
        chart.y_axis_max = opts.y_max
        chart.x_axis_major_unit = opts.x_major_unit
        chart.x_axis_minor_unit = opts.x_minor_unit
        chart.y_axis_major_unit = opts.y_major_unit
        chart.y_axis_minor_unit = opts.y_minor_unit
        chart.show_grid = opts.show_grid
        chart.connect_line = opts.connect_line
        # 系列：用关系集合清空 + 追加，保证内存集合同步（级联删除旧系列）
        chart.series_list.clear()
        self.db.flush()
        for i, scfg in enumerate(self.series_view.get_series()):
            chart.series_list.append(Series(series_name=scfg.name,
                                            x_col_letter=scfg.x_col, y_col_letter=scfg.y_col,
                                            row_start=scfg.row_start, row_end=scfg.row_end,
                                            color_hex=scfg.color, marker_shape=scfg.shape,
                                            marker_size=scfg.size, sort_order=i))
        # 限值规则：清空 + 追加（X 区间 → Y 上下限）
        chart.limits.clear()
        self.db.flush()
        for i, rule in enumerate(self.options_view._rules):
            chart.limits.append(ChartLimit(x_col_letter=rule.x_col, y_col_letter=rule.y_col,
                                           x_start=rule.x_start, x_end=rule.x_end,
                                           y_min=rule.y_min, y_max=rule.y_max, sort_order=i))
        self.db.commit()

    def _preview(self):
        if not self.current_chart or self.source_slice is None:
            return
        series = self.series_view.get_series()
        opts = self.options_view.get_options()
        self.preview.render(self.source_slice, series, opts)

    # ================= 导入 =================
    def _import(self, path, start_row, end_row, start_col, end_col):
        if not self.current_project:
            QMessageBox.information(self, "提示", "请先在左侧选择或新建一个项目（数据表）")
            return
        self.source_name = os.path.basename(path)
        self._run_import(path, start_row, end_row, start_col, end_col)

    def _run_import(self, path, start_row, end_row, start_col, end_col, read_raw=False):
        self.statusBar().showMessage("正在读取数据…")
        self._import_worker = ImportWorker(path, start_row, end_row, start_col, end_col, read_raw, self)
        self._import_worker.success.connect(self._on_import_done)
        self._import_worker.failed.connect(self._on_import_failed)
        self._import_worker.cancelled.connect(lambda: self.statusBar().showMessage("导入已取消"))
        self._import_worker.start()

    def _on_import_done(self, sl: SheetSlice):
        self.source_slice = sl
        self.import_view.set_max_row(sl.row_count)
        p = self.current_project
        p.data_start_row = sl.start_row
        p.data_end_row = sl.end_row
        p.data_start_col_letter = sl.column_letters[0]
        p.data_end_col_letter = sl.column_letters[-1]
        self.db.commit()
        if self.current_chart:
            self._load_chart(self.current_chart)
        else:
            self.series_view.set_series([], self._columns())
            QMessageBox.information(self, "提示", "数据已加载。请先点击「＋新建图表」创建一张图，再配置系列。")
        self.statusBar().showMessage(f"已加载 {sl.row_count:,} 行数据")
        self.tabs.setCurrentWidget(self.series_view)

    def _on_import_failed(self, msg: str):
        self.statusBar().showMessage("读取失败")
        QMessageBox.critical(self, "读取失败", msg)

    # ================= CRUD =================
    def _default_group(self) -> ProjectGroup:
        g = self.db.query(ProjectGroup).filter(ProjectGroup.name == DEFAULT_GROUP).first()
        if not g:
            g = ProjectGroup(name=DEFAULT_GROUP, sort_order=0)
            self.db.add(g)
            self.db.commit()
        return g

    def _add_group(self):
        name, ok = QInputDialog.getText(self, "新建项目组", "项目组名称：")
        if ok and name.strip():
            if self.db.query(ProjectGroup).filter(ProjectGroup.name == name.strip()).first():
                QMessageBox.warning(self, "提示", "项目组名称已存在")
                return
            mx = max([g.sort_order for g in self._groups()] or [0])
            self.db.add(ProjectGroup(name=name.strip(), sort_order=mx + 1))
            self.db.commit()
            self._refresh_tree()

    def _delete_group(self):
        g = self.current_group
        if not g:
            QMessageBox.information(self, "提示", "请先在左侧选中一个项目组")
            return
        if QMessageBox.question(self, "删除项目组",
                                f"确定删除项目组「{g.name}」及其下所有项目/图表？\n（磁盘文件不会被删除）") != QMessageBox.StandardButton.Yes:
            return
        self.db.delete(g)
        self.db.commit()
        self.current_group = None
        self.current_project = None
        self.current_chart = None
        self.source_slice = None
        self._refresh_all()

    def _add_project(self):
        """新建项目（数据表）——加入【当前选中的项目组】，未选中则用第一个组。"""
        groups = self._groups()
        if not groups:
            self._default_group()
            groups = self._groups()
        if self.current_group is None:
            self.current_group = groups[0]
        name, ok = QInputDialog.getText(
            self, "新建项目",
            f"项目名称（= 一个原始数据表格，将加入项目组「{self.current_group.name}」）：")
        if not ok or not name.strip():
            return
        p = Project(name=name.strip(), group_id=self.current_group.id, source_file_path="",
                    data_start_row=1, data_end_row=None,
                    data_start_col_letter="A", data_end_col_letter=None,
                    status=ACTIVE, last_opened_at=datetime.now())
        self.db.add(p)
        self.db.commit()
        self.current_project = p
        self.current_chart = None
        self.source_slice = None
        self._refresh_all()
        self.tabs.setCurrentWidget(self.import_view)
        self.statusBar().showMessage(f"已新建项目「{p.name}」，请到数据设置页导入原始数据")

    def _delete_project(self):
        if not self.current_project:
            QMessageBox.information(self, "提示", "请先在左侧选中一个项目")
            return
        p = self.current_project
        if QMessageBox.question(self, "删除项目",
                                f"确定删除项目「{p.name}」？\n（磁盘文件不会被删除）") != QMessageBox.StandardButton.Yes:
            return
        self.db.delete(p)
        self.db.commit()
        self.current_project = None
        self.current_chart = None
        self.source_slice = None
        self._refresh_all()

    def _copy_project(self, src_project=None):
        """复制选中的项目及其全部图表/系列/限值规则，在同一项目组下新建一份副本。"""
        src = src_project or self.current_project
        if not src:
            QMessageBox.information(self, "提示", "请先选中要复制的项目")
            return
        # 先同步当前编辑状态
        self._sync_current_chart()

        new_project = Project(
            name=f"{src.name} 副本",
            group_id=src.group_id,
            source_file_path=src.source_file_path,  # 共享同一导出文件
            data_start_row=src.data_start_row,
            data_end_row=src.data_end_row,
            data_start_col_letter=src.data_start_col_letter,
            data_end_col_letter=src.data_end_col_letter,
            status=src.status,
            last_opened_at=None,
        )
        self.db.add(new_project)
        self.db.flush()  # 获取 new_project.id

        # 深复制全部图表及其子记录
        for src_chart in src.charts:
            new_chart = Chart(
                chart_name=src_chart.chart_name,
                chart_title=src_chart.chart_title,
                x_axis_label=src_chart.x_axis_label,
                y_axis_label=src_chart.y_axis_label,
                x_axis_min=src_chart.x_axis_min,
                x_axis_max=src_chart.x_axis_max,
                y_axis_min=src_chart.y_axis_min,
                y_axis_max=src_chart.y_axis_max,
                x_axis_major_unit=src_chart.x_axis_major_unit,
                x_axis_minor_unit=src_chart.x_axis_minor_unit,
                y_axis_major_unit=src_chart.y_axis_major_unit,
                y_axis_minor_unit=src_chart.y_axis_minor_unit,
                show_grid=src_chart.show_grid,
                connect_line=src_chart.connect_line,
                sort_order=src_chart.sort_order,
            )
            new_project.charts.append(new_chart)
            self.db.flush()  # 获取 new_chart.id

            # 深复制系列
            for s in src_chart.series_list:
                new_chart.series_list.append(Series(
                    series_name=s.series_name,
                    x_col_letter=s.x_col_letter,
                    y_col_letter=s.y_col_letter,
                    row_start=s.row_start,
                    row_end=s.row_end,
                    color_hex=s.color_hex,
                    marker_shape=s.marker_shape,
                    marker_size=s.marker_size,
                    sort_order=s.sort_order,
                ))

            # 深复制限值规则
            for lim in src_chart.limits:
                new_chart.limits.append(ChartLimit(
                    x_col_letter=lim.x_col_letter,
                    y_col_letter=lim.y_col_letter,
                    x_start=lim.x_start,
                    x_end=lim.x_end,
                    y_min=lim.y_min,
                    y_max=lim.y_max,
                    sort_order=lim.sort_order,
                ))

        self.db.commit()
        # 切换到新项目
        self.current_group = new_project.group
        self.current_project = new_project
        self.current_chart = new_project.charts[0] if new_project.charts else None
        self.source_slice = None
        self._refresh_all()
        self.tabs.setCurrentWidget(self.series_view)
        self.statusBar().showMessage(
            f"已复制项目「{src.name}」→「{new_project.name}」"
            f"（{len(new_project.charts)} 张图表）"
        )

    def _add_chart(self):
        if not self.current_project:
            QMessageBox.information(self, "提示", "请先选择项目")
            return
        self._sync_current_chart()
        n = len(self.current_project.charts) + 1
        c = Chart(chart_name=f"图表 {n}", show_grid=True, connect_line=True, sort_order=n - 1)
        self.current_project.charts.append(c)   # 通过关系追加，保证集合同步
        self.db.commit()
        self.current_chart = c
        self._load_chart(c)
        self._refresh_all()
        self.tabs.setCurrentWidget(self.series_view)

    def _copy_chart(self, src_chart=None):
        """复制选中的图表及其全部系列/限值规则，在同一项目下新建一张副本。"""
        src = src_chart or self.current_chart or self.chart_list.selected_chart()
        if not src:
            QMessageBox.information(self, "提示", "请先选中要复制的图表")
            return
        # 先同步当前图表，防止数据丢失
        self._sync_current_chart()
        # 确保源图表数据也是最新的
        if self.current_chart and self.current_chart.id != src.id:
            pass  # src 不是当前编辑图表，DB 中已是最新
        else:
            # src 就是当前编辑图表，_sync_current_chart 已保存
            pass

        n = len(self.current_project.charts) + 1
        new_chart = Chart(
            chart_name=f"{src.chart_name} 副本",
            chart_title=src.chart_title,
            x_axis_label=src.x_axis_label,
            y_axis_label=src.y_axis_label,
            x_axis_min=src.x_axis_min,
            x_axis_max=src.x_axis_max,
            y_axis_min=src.y_axis_min,
            y_axis_max=src.y_axis_max,
            x_axis_major_unit=src.x_axis_major_unit,
            x_axis_minor_unit=src.x_axis_minor_unit,
            y_axis_major_unit=src.y_axis_major_unit,
            y_axis_minor_unit=src.y_axis_minor_unit,
            show_grid=src.show_grid,
            connect_line=src.connect_line,
            sort_order=n - 1,
        )
        self.current_project.charts.append(new_chart)
        self.db.flush()  # 获取 new_chart.id

        # 深复制全部系列
        for s in src.series_list:
            new_chart.series_list.append(Series(
                series_name=s.series_name,
                x_col_letter=s.x_col_letter,
                y_col_letter=s.y_col_letter,
                row_start=s.row_start,
                row_end=s.row_end,
                color_hex=s.color_hex,
                marker_shape=s.marker_shape,
                marker_size=s.marker_size,
                sort_order=s.sort_order,
            ))

        # 深复制全部限值规则
        for lim in src.limits:
            new_chart.limits.append(ChartLimit(
                x_col_letter=lim.x_col_letter,
                y_col_letter=lim.y_col_letter,
                x_start=lim.x_start,
                x_end=lim.x_end,
                y_min=lim.y_min,
                y_max=lim.y_max,
                sort_order=lim.sort_order,
            ))

        self.db.commit()
        self.current_chart = new_chart
        self._load_chart(new_chart)
        self._refresh_all()
        self.tabs.setCurrentWidget(self.series_view)
        self.statusBar().showMessage(f"已复制图表「{src.chart_name}」→「{new_chart.chart_name}」")

    def _delete_chart(self):
        c = self.current_chart or self.chart_list.selected_chart()
        if not c:
            QMessageBox.information(self, "提示", "请先选中一张图表")
            return
        if QMessageBox.question(self, "删除图表", f"确定删除图表「{c.chart_name}」？") != QMessageBox.StandardButton.Yes:
            return
        self.db.delete(c)
        self.db.commit()
        self.current_chart = None
        self._refresh_all()

    # ================= 导出 =================
    def _export(self):
        if self.source_slice is None:
            QMessageBox.information(self, "提示", "请先在数据设置页导入原始数据")
            return
        self._sync_current_chart()
        specs: list[ChartSpec] = []
        for chart in self.current_project.charts:
            opts = ChartOptions(
                title=chart.chart_title, x_label=chart.x_axis_label, y_label=chart.y_axis_label,
                x_min=chart.x_axis_min, x_max=chart.x_axis_max, y_min=chart.y_axis_min, y_max=chart.y_axis_max,
                x_major_unit=chart.x_axis_major_unit, x_minor_unit=chart.x_axis_minor_unit,
                y_major_unit=chart.y_axis_major_unit, y_minor_unit=chart.y_axis_minor_unit,
                show_grid=chart.show_grid, connect_line=chart.connect_line,
                rules=[LimitRule(x_col=l.x_col_letter, y_col=l.y_col_letter,
                                 x_start=l.x_start, x_end=l.x_end, y_min=l.y_min, y_max=l.y_max)
                       for l in chart.limits])
            series = [SeriesConfig(name=s.series_name, x_col=s.x_col_letter, y_col=s.y_col_letter,
                                   row_start=s.row_start, row_end=s.row_end, color=s.color_hex,
                                   shape=s.marker_shape, size=s.marker_size) for s in chart.series_list]
            specs.append(ChartSpec(chart_name=chart.chart_name, options=opts, series_list=series))
        if not specs:
            QMessageBox.information(self, "提示", "请先新建至少一张图表")
            return

        p = self.current_project
        if p.source_file_path and os.path.isfile(p.source_file_path):
            default_path = p.source_file_path
        else:
            default_path = default_export_name(self.source_name or p.name or "散点图")
        dlg = ExportDialog(self.source_slice, specs, default_path, self)
        if dlg.exec() == ExportDialog.DialogCode.Accepted:
            path = dlg.result_path
            p.source_file_path = path
            p.status = ACTIVE
            p.last_opened_at = datetime.now()
            self.db.commit()
            self._refresh_all()
            self.statusBar().showMessage(f"导出完成：{path}")

    # ================= 其他 =================
    def _on_recent_clicked(self, item: QListWidgetItem):
        pid = item.data(Qt.ItemDataRole.UserRole)
        p = self.db.get(Project, pid)
        if p:
            self._on_project_selected(p)

    def _probe_async(self):
        self.statusBar().showMessage("正在后台探活文件状态…")
        self._probe_worker = ProbeWorker(self)
        self._probe_worker.done.connect(self._on_probe_done)
        self._probe_worker.failed.connect(lambda m: self.statusBar().showMessage(f"探活失败：{m}"))
        self._probe_worker.start()

    def _on_probe_done(self):
        self.db.expire_all()
        self._refresh_all()
        self.statusBar().showMessage("就绪")

    def closeEvent(self, event):
        self._sync_current_chart()
        self.db.close()
        super().closeEvent(event)


def _hbox(widgets):
    from PySide6.QtWidgets import QHBoxLayout
    h = QHBoxLayout()
    for w in widgets:
        h.addWidget(w)
    return h


def run_app() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()
