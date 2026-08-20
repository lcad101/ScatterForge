"""导出对话框（进度条 + 取消，冻结规范第 7 章）。"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QPushButton, QVBoxLayout,
)

from src.core.exceptions import OperationCancelledException
from src.services.chart_builder import ChartOptions, SeriesConfig
from src.services.excel_export_service import ExcelExportService
from src.services.excel_handler import SheetSlice


class ExportWorker(QThread):
    progress = Signal(int)
    success = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, sl: SheetSlice, series: list[SeriesConfig], options: ChartOptions,
                 target_path: str, parent=None):
        super().__init__(parent)
        self._service = ExcelExportService()
        self._sl = sl
        self._series = series
        self._options = options
        self._path = target_path

    def cancel(self) -> None:
        self._service.cancel()

    def run(self) -> None:
        try:
            path = self._service.export(self._sl, self._series, self._options, self._path,
                                        progress_cb=self.progress.emit)
            self.success.emit(path)
        except OperationCancelledException:
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ExportDialog(QDialog):
    def __init__(self, sl: SheetSlice, series: list[SeriesConfig], options: ChartOptions,
                 default_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📈 导出图表")
        self.setMinimumWidth(480)
        self._sl = sl
        self._series = series
        self._options = options
        self._worker: ExportWorker | None = None

        self.path_edit = QLineEdit(default_path)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)

        self.info = QLabel(
            "Sheet 1 = raw data（数据切片）· Sheet 2 = Chart View（原生散点图）\n"
            "覆盖已存在文件前会自动备份；取消后自动回滚（删临时文件 / 恢复备份）。"
        )
        self.info.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.pct = QLabel("0%")

        prog_row = QHBoxLayout()
        prog_row.addWidget(self.progress, 1)
        prog_row.addWidget(self.pct)

        self.cancel_btn = QPushButton("✖ 取消")
        self.cancel_btn.clicked.connect(self._cancel)
        self.start_btn = QPushButton("🚀 开始导出")
        self.start_btn.clicked.connect(self._start)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.start_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("目标文件："))
        layout.addLayout(path_row)
        layout.addWidget(self.info)
        layout.addWidget(QLabel("导出进度："))
        layout.addLayout(prog_row)
        layout.addLayout(btn_row)

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存导出文件", self.path_edit.text(), "Excel 文件 (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            self.path_edit.setText(path)

    def _start(self) -> None:
        target = self.path_edit.text().strip()
        if not target:
            return
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)
        self.pct.setText("0%")

        self._worker = ExportWorker(self._sl, self._series, self._options, target, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.success.connect(self._on_success)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, value: int) -> None:
        self.progress.setValue(value)
        self.pct.setText(f"{value}%")

    def _on_success(self, path: str) -> None:
        self._result = path
        self.accept()

    def _on_failed(self, msg: str) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "导出失败", msg)

    def _on_cancelled(self) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setValue(0)
        self.pct.setText("已取消")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "已取消", "导出已取消，已回滚（删除临时文件 / 恢复备份）。")

    @property
    def result_path(self) -> str:
        return getattr(self, "_result", "")


def default_export_name(source_name: str) -> str:
    """生成默认导出文件名：原文件名_Scatter_{时间戳}.xlsx"""
    import os
    base = os.path.splitext(os.path.basename(source_name))[0]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = os.path.dirname(source_name) or "."
    return os.path.join(directory, f"{base}_Scatter_{stamp}.xlsx")
