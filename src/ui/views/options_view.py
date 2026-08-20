"""图表选项页（标题/轴标签/轴范围/网格）。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from src.services.chart_builder import ChartOptions


def _parse_float(text: str):
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


class OptionsView(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title = QLineEdit()
        self.x_label = QLineEdit()
        self.y_label = QLineEdit()
        self.x_min = QLineEdit()
        self.x_max = QLineEdit()
        self.y_min = QLineEdit()
        self.y_max = QLineEdit()
        self.show_grid = QCheckBox("显示网格线")
        self.show_grid.setChecked(True)

        for w in (self.x_min, self.x_max, self.y_min, self.y_max):
            w.setPlaceholderText("自动")
            w.textChanged.connect(self.changed.emit)
        for w in (self.title, self.x_label, self.y_label):
            w.textChanged.connect(self.changed.emit)
        self.show_grid.toggled.connect(self.changed.emit)

        form = QFormLayout()
        form.addRow("图表标题", self.title)
        form.addRow("X 轴标签", self.x_label)
        form.addRow("Y 轴标签", self.y_label)
        form.addRow("X 轴最小值", self.x_min)
        form.addRow("X 轴最大值", self.x_max)
        form.addRow("Y 轴最小值", self.y_min)
        form.addRow("Y 轴最大值", self.y_max)
        form.addRow("", self.show_grid)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch(1)

    def get_options(self) -> ChartOptions:
        return ChartOptions(
            title=self.title.text().strip() or None,
            x_label=self.x_label.text().strip() or None,
            y_label=self.y_label.text().strip() or None,
            x_min=_parse_float(self.x_min.text()),
            x_max=_parse_float(self.x_max.text()),
            y_min=_parse_float(self.y_min.text()),
            y_max=_parse_float(self.y_max.text()),
            show_grid=self.show_grid.isChecked(),
        )

    def set_options(self, options: ChartOptions) -> None:
        self.title.setText(options.title or "")
        self.x_label.setText(options.x_label or "")
        self.y_label.setText(options.y_label or "")
        self.x_min.setText("" if options.x_min is None else str(options.x_min))
        self.x_max.setText("" if options.x_max is None else str(options.x_max))
        self.y_min.setText("" if options.y_min is None else str(options.y_min))
        self.y_max.setText("" if options.y_max is None else str(options.y_max))
        self.show_grid.setChecked(options.show_grid)
