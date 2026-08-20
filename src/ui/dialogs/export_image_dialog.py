"""导出图片对话框（PNG / SVG，冻结规范 2026-08-20 Q4）。"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout,
)

RESOLUTIONS = [("1920 × 1080", 1920, 1080), ("3840 × 2160", 3840, 2160), ("1280 × 720", 1280, 720)]


class ExportImageDialog(QDialog):
    def __init__(self, preview, default_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📷 导出为图片")
        self.setMinimumWidth(420)
        self._preview = preview

        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "SVG"])

        self.res_combo = QComboBox()
        for label, _, _ in RESOLUTIONS:
            self.res_combo.addItem(label)

        self.path_edit = QLineEdit(default_name)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)

        form = QFormLayout()
        form.addRow("格式", self.format_combo)
        form.addRow("分辨率", self.res_combo)
        form.addRow("保存位置", path_row)

        self.status = QLabel("")
        self.status.setWordWrap(True)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(export_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addLayout(btn_row)

    def _browse(self) -> None:
        fmt = self.format_combo.currentText().lower()
        path, _ = QFileDialog.getSaveFileName(self, "保存图片", self.path_edit.text(), f"{fmt.upper()} 文件 (*.{fmt})")
        if path:
            self.path_edit.setText(path)

    def _export(self) -> None:
        fmt = self.format_combo.currentText()
        _, width, height = RESOLUTIONS[self.res_combo.currentIndex()]
        target = self.path_edit.text().strip()
        if not target:
            return
        ext = f".{fmt.lower()}"
        if not target.lower().endswith(ext):
            target += ext
        try:
            self.status.setText("正在导出…")
            self._preview.export_image(fmt, target, width, height)
            self.status.setText(f"✅ 已导出：{target}")
            self.path_edit.setText(target)
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"❌ 导出失败：{exc}")
