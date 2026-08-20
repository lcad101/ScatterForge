"""数据设置页（导入页）。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.core.exceptions import ValidationError
from src.models.validators import validate_col_in_range, validate_col_letter


class ImportView(QWidget):
    """选择原始 Excel + 设定行列范围，发出 applyRequested 请求读取切片。"""

    applyRequested = Signal(str, int, object, str, object)  # (path, start_row, end_row, start_col, end_col)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = ""

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("选择原始 Excel 文件（一次性数据源）")

        self.start_row = QSpinBox()
        self.start_row.setRange(1, 10_000_000)
        self.start_row.setValue(1)
        self.start_row.setToolTip("数据行号（不含表头），表头为第 1 行")

        self.end_row = QSpinBox()
        self.end_row.setRange(0, 10_000_000)
        self.end_row.setValue(0)
        self.end_row.setSpecialValueText("自动（全部行）")
        self.end_row.setToolTip("0 = 自动到末行；结合下方勾选可仅取一行")

        self.single_row = QCheckBox("结束行留空：仅取起始行这一行")

        self.start_col = QLineEdit("A")
        self.start_col.setMaxLength(3)
        self.start_col.setToolTip("起始列字母，A~ZZZ")

        self.end_col = QLineEdit()
        self.end_col.setMaxLength(3)
        self.end_col.setPlaceholderText("留空 = 仅取一列")
        self.end_col.setToolTip("结束列字母；留空仅取起始列一列")

        self.max_row_label = QLabel("文件总行数：—")

        layout = QVBoxLayout(self)

        # 文件选择
        file_row = QHBoxLayout()
        file_row.addWidget(self.file_edit, 1)
        browse_btn = QPushButton("📂 选择…")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)
        layout.addWidget(QLabel("原始数据文件"))
        layout.addLayout(file_row)

        # 行范围
        form = QFormLayout()
        form.addRow("起始行", self.start_row)
        form.addRow("结束行", self.end_row)
        form.addRow("", self.single_row)
        layout.addLayout(form)
        layout.addWidget(self.max_row_label)

        # 列范围
        form2 = QFormLayout()
        form2.addRow("起始列", self.start_col)
        form2.addRow("结束列", self.end_col)
        layout.addLayout(form2)

        hint = QLabel("💡 预览 >5,000 行仅展示前 5,000 点，导出仍写入全部行数。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8a6d1a;background:#fff8e6;border:1px solid #f3dfa8;padding:6px;border-radius:4px;")
        layout.addWidget(hint)

        apply_btn = QPushButton("✅ 应用范围并配置系列")
        apply_btn.clicked.connect(self._apply)
        layout.addWidget(apply_btn)
        layout.addStretch(1)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择原始 Excel", "", "Excel 文件 (*.xlsx *.xlsm)")
        if path:
            self._path = path
            self.file_edit.setText(path)

    def set_max_row(self, n: int) -> None:
        self.max_row_label.setText(f"文件总行数：{n:,}（数据行）")

    def _apply(self) -> None:
        if not self._path:
            self._warn("请先选择原始 Excel 文件")
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
            if ec and self._col_idx(sc) > self._col_idx(ec):
                raise ValidationError("起始列必须 ≤ 结束列")
        except ValidationError as exc:
            self._warn(str(exc))
            return

        end_row = None if self.single_row.isChecked() else (self.end_row.value() or None)
        self.applyRequested.emit(self._path, self.start_row.value(), end_row, sc, ec)

    @staticmethod
    def _col_idx(col: str) -> int:
        from src.models.validators import col_to_index
        return col_to_index(col)

    def _warn(self, msg: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "输入有误", msg)
