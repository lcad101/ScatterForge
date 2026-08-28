"""数据设置页（v3.3）：初始化 → 配置行列范围 → 应用。

流程：用户选择原始文件 → 初始化（复制到保存路径）→ 配置起止行列 → 应用。
所有操作基于 DB 中持久化的副本，原始文件仅用于初始化时复制。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.core.exceptions import ValidationError
from src.models.validators import col_to_index, validate_col_in_range, validate_col_letter


class ImportView(QWidget):
    initRequested = Signal()    # 用户点击初始化数据
    reinitRequested = Signal()  # 用户点击重新初始化
    applyRequested = Signal(str, int, object, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_path = ""
        self._saved_path = ""

        layout = QVBoxLayout(self)

        # ====== Section 1: 原始文件 + 初始化 ======
        layout.addWidget(QLabel("① 初始化数据文件"))
        self.source_edit = QLineEdit()
        self.source_edit.setReadOnly(True)
        self.source_edit.setPlaceholderText("选择原始 Excel 文件（将复制一份到指定保存路径）")
        src_row = QHBoxLayout()
        src_row.addWidget(self.source_edit, 1)
        src_browse = QPushButton("📂 选择原始文件…")
        src_browse.clicked.connect(self._browse_source)
        src_row.addWidget(src_browse)
        layout.addLayout(src_row)

        init_btn = QPushButton("✅ 初始化数据（复制文件并读取表格信息）")
        init_btn.clicked.connect(self._on_init)
        layout.addWidget(init_btn)

        # ====== Section 2: 初始化结果 ======
        layout.addWidget(QLabel("② 数据文件信息"))
        self.saved_path_edit = QLineEdit()
        self.saved_path_edit.setReadOnly(True)
        self.saved_path_edit.setPlaceholderText("初始化后显示保存路径")
        saved_row = QHBoxLayout()
        saved_row.addWidget(self.saved_path_edit, 1)
        reinit_btn = QPushButton("🔄 重新初始化")
        reinit_btn.clicked.connect(self._on_reinit)
        saved_row.addWidget(reinit_btn)
        layout.addLayout(saved_row)

        self.info_label = QLabel("文件总行数：— · 总列数：—")
        layout.addWidget(self.info_label)

        # ====== Section 3: 数据配置 ======
        layout.addWidget(QLabel("③ 配置行列范围（基于保存路径上的表格）"))
        self.start_row = QSpinBox()
        self.start_row.setRange(1, 10_000_000)
        self.start_row.setValue(1)
        self.end_row = QSpinBox()
        self.end_row.setRange(0, 10_000_000)
        self.end_row.setValue(0)
        self.end_row.setSpecialValueText("仅取起始行")
        self.start_col = QLineEdit("A")
        self.start_col.setMaxLength(3)
        self.end_col = QLineEdit()
        self.end_col.setMaxLength(3)
        self.end_col.setPlaceholderText("留空 = 仅取起始列")

        form = QFormLayout()
        form.addRow("起始行（真实行号）", self.start_row)
        form.addRow("结束行（真实行号）", self.end_row)
        form.addRow("起始列（字母）", self.start_col)
        form.addRow("结束列（字母）", self.end_col)
        layout.addLayout(form)

        hint = QLabel("💡 无「表头在第 1 行」假设：起止行列均按真实 Excel 行列号。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8a6d1a;background:#fff8e6;border:1px solid #f3dfa8;padding:6px;border-radius:4px;")
        layout.addWidget(hint)

        # ====== Section 4: 操作 ======
        apply_btn = QPushButton("✅ 应用范围并配置图表")
        apply_btn.clicked.connect(self._apply)
        layout.addWidget(apply_btn)
        layout.addStretch(1)

    def _browse_source(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择原始 Excel", "", "Excel 文件 (*.xlsx *.xlsm)")
        if path:
            self._source_path = path
            self.source_edit.setText(path)

    def _on_init(self):
        self.initRequested.emit()

    def _on_reinit(self):
        self.reinitRequested.emit()

    def set_init_result(self, saved_path, total_rows, total_cols, end_row, end_col):
        self._saved_path = saved_path
        self.saved_path_edit.setText(saved_path)
        self.info_label.setText(
            f"文件总行数：{total_rows:,} · 总列数：{total_cols:,}"
            f"（最后行号 {end_row}，最后列 {end_col}）")
        self.end_row.setValue(end_row)
        self.end_col.setText(end_col)

    def set_row_col_range(self, start_row: int, end_row: int | None, start_col: str, end_col: str | None):
        """恢复项目保存的行列范围到 UI 控件。"""
        self.start_row.setValue(start_row)
        self.end_row.setValue(end_row or 0)
        self.start_col.setText(start_col)
        self.end_col.setText(end_col or "")

    def set_saved_path(self, path):
        self._saved_path = path
        self.saved_path_edit.setText(path)

    def set_max_row(self, n):
        self.info_label.setText(f"文件总行数：{n:,}")

    def _apply(self):
        if not self._saved_path:
            QMessageBox.warning(self, "提示", "请先初始化数据文件")
            return
        try:
            sc = self.start_col.text().strip().upper()
            ec = self.end_col.text().strip().upper() or None
            if not validate_col_letter(sc):
                raise ValidationError(f"起始列无效：{sc}")
            if ec and not validate_col_letter(ec):
                raise ValidationError(f"结束列无效：{ec}")
            if not validate_col_in_range(sc):
                raise ValidationError(f"起始列超出 Excel 最大列数（XFD）：{sc}")
            if ec and not validate_col_in_range(ec):
                raise ValidationError(f"结束列超出 Excel 最大列数（XFD）：{ec}")
            if ec and col_to_index(sc) > col_to_index(ec):
                raise ValidationError("起始列必须 ≤ 结束列")
        except ValidationError as exc:
            QMessageBox.warning(self, "输入有误", str(exc))
            return
        end_row = self.end_row.value() or None
        self.applyRequested.emit(self._saved_path, self.start_row.value(), end_row, sc, ec)
