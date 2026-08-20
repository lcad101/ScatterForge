"""系列配置页（冻结规范第 6 章 + 2026-08-20 Q2/Q4）。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
    QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from src.models.validators import EXCEL_SAFE_COLORS, EXCEL_SAFE_COLOR_NAMES, MarkerShape
from src.services.chart_builder import SeriesConfig

SHAPE_GLYPHS = {"circle": "●", "diamond": "◆", "square": "■", "triangle": "▲"}


def _color_icon(hex_color: str) -> QIcon:
    pm = QPixmap(16, 16)
    pm.fill(QColor(hex_color))
    return QIcon(pm)


class SeriesRowWidget(QWidget):
    changed = Signal()

    def __init__(self, cfg: SeriesConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg

        self.name_edit = QLineEdit(cfg.name)
        self.name_edit.setPlaceholderText("系列名称")
        self.name_edit.textChanged.connect(self._on_name)

        self.x_edit = QLineEdit(cfg.x_col)
        self.x_edit.setMaxLength(3)
        self.x_edit.setFixedWidth(48)
        self.x_edit.textChanged.connect(self._on_x)

        self.y_edit = QLineEdit(cfg.y_col)
        self.y_edit.setMaxLength(3)
        self.y_edit.setFixedWidth(48)
        self.y_edit.textChanged.connect(self._on_y)

        self.color_btn = QToolButton()
        self.color_btn.setIcon(_color_icon(cfg.color))
        self.color_btn.setToolTip("选择颜色（仅 16 种标准色）")
        self.color_btn.clicked.connect(self._pop_palette)

        self.shape_group = QButtonGroup(self)
        self.shape_group.setExclusive(True)
        self.shape_buttons = {}
        shape_row = QHBoxLayout()
        shape_row.setSpacing(2)
        for shape in MarkerShape:
            btn = QPushButton(SHAPE_GLYPHS[shape.value])
            btn.setCheckable(True)
            btn.setFixedWidth(30)
            btn.setToolTip(shape.value)
            btn.setChecked(shape.value == cfg.shape)
            btn.clicked.connect(lambda _=False, s=shape.value: self._on_shape(s))
            self.shape_group.addButton(btn)
            self.shape_buttons[shape.value] = btn
            shape_row.addWidget(btn)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(3, 20)
        self.size_spin.setValue(cfg.size)
        self.size_spin.setFixedWidth(54)
        self.size_spin.valueChanged.connect(self._on_size)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("名称"))
        layout.addWidget(self.name_edit, 1)
        layout.addWidget(QLabel("X 列"))
        layout.addWidget(self.x_edit)
        layout.addWidget(QLabel("Y 列"))
        layout.addWidget(self.y_edit)
        layout.addWidget(self.color_btn)
        layout.addLayout(shape_row)
        layout.addWidget(QLabel("大小"))
        layout.addWidget(self.size_spin)

    # ---- 事件 ----
    def _on_name(self, text: str) -> None:
        self.cfg.name = text.strip() or f"系列"
        self.changed.emit()

    def _on_x(self, text: str) -> None:
        self.cfg.x_col = text.strip().upper()
        self.changed.emit()

    def _on_y(self, text: str) -> None:
        self.cfg.y_col = text.strip().upper()
        self.changed.emit()

    def _on_shape(self, shape: str) -> None:
        self.cfg.shape = shape
        self.changed.emit()

    def _on_size(self, value: int) -> None:
        self.cfg.size = value
        self.changed.emit()

    def _pop_palette(self) -> None:
        menu = QMenu(self)
        for name, hex_color in zip(EXCEL_SAFE_COLOR_NAMES, EXCEL_SAFE_COLORS):
            act = menu.addAction(_color_icon(hex_color), f"{name}  {hex_color}")
            act.triggered.connect(lambda _=False, c=hex_color: self._set_color(c))
        menu.exec(self.color_btn.mapToGlobal(self.color_btn.rect().bottomLeft()))

    def _set_color(self, color: str) -> None:
        self.cfg.color = color
        self.color_btn.setIcon(_color_icon(color))
        self.changed.emit()


class ConfigView(QWidget):
    changed = Signal()
    exportRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: list[SeriesConfig] = []
        self._rows: list[SeriesRowWidget] = []

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)

        add_btn = QPushButton("＋ 添加系列")
        add_btn.clicked.connect(self.add_series)

        self.export_btn = QPushButton("📈 下一步：导出图表")

        layout = QVBoxLayout(self)
        layout.addLayout(self.rows_layout)
        layout.addWidget(add_btn)
        layout.addWidget(self.export_btn)
        layout.addStretch(1)
        self.export_btn.clicked.connect(self.exportRequested.emit)

    # ---- 数据 ----
    def set_series(self, series: list[SeriesConfig]) -> None:
        self._series = series
        self._rebuild()

    def get_series(self) -> list[SeriesConfig]:
        return list(self._series)

    def add_series(self) -> None:
        self._series.append(SeriesConfig(
            name=f"系列 {len(self._series) + 1}",
            x_col=self._series[-1].x_col if self._series else "A",
            y_col=self._series[-1].y_col if self._series else "B",
            color=EXCEL_SAFE_COLORS[len(self._series) % 16],
            shape="circle", size=8,
        ))
        self._rebuild()
        self.changed.emit()

    def remove_series(self, index: int) -> None:
        if 0 <= index < len(self._series):
            del self._series[index]
            self._rebuild()
            self.changed.emit()

    def _rebuild(self) -> None:
        # 清空
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._rows = []
        for i, cfg in enumerate(self._series):
            row = SeriesRowWidget(cfg)
            row.changed.connect(self.changed.emit)
            del_btn = QPushButton("🗑")
            del_btn.setFixedWidth(34)
            del_btn.setToolTip("删除系列")
            del_btn.clicked.connect(lambda _=False, idx=i: self.remove_series(idx))
            wrap = QWidget()
            hl = QHBoxLayout(wrap)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(row, 1)
            hl.addWidget(del_btn)
            self.rows_layout.addWidget(wrap)
            self._rows.append(row)
