"""系列配置页（v3.2）：系列增删改查，每系列必填 X 列 + Y 列 + 行范围。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
    QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from src.models.validators import EXCEL_SAFE_COLORS, EXCEL_SAFE_COLOR_NAMES, MarkerShape
from src.services.chart_builder import SeriesConfig

SHAPE_GLYPHS = {"circle": "●", "diamond": "◆", "square": "■", "triangle": "▲"}


def _color_icon(hex_color: str) -> QIcon:
    pm = QPixmap(16, 16)
    pm.fill(QColor(hex_color))
    return QIcon(pm)


def _combo_items(columns: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """columns: [(列字母, 表头名)] → 展示 'A · 表头'，存列字母。"""
    return columns if columns else [("A", "A")]


class SeriesRowWidget(QWidget):
    changed = Signal()

    def __init__(self, cfg: SeriesConfig, columns: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.cfg = cfg

        self.visible_cb = QCheckBox("显示")
        self.visible_cb.setChecked(getattr(cfg, "visible", True))
        self.visible_cb.setToolTip("勾选后在预览中显示该系列")
        self.visible_cb.toggled.connect(lambda v: self._set("visible", v))

        self.name_edit = QLineEdit(cfg.name)
        self.name_edit.setPlaceholderText("系列名称")
        self.name_edit.textChanged.connect(lambda t: self._set("name", t.strip() or "系列"))

        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        for combo, cur in ((self.x_combo, cfg.x_col), (self.y_combo, cfg.y_col)):
            for letter, header in _combo_items(columns):
                combo.addItem(f"{letter} · {header}", letter)
            idx = combo.findData(cur)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        self.x_combo.currentIndexChanged.connect(lambda _=0: self._set("x_col", self.x_combo.currentData()))
        self.y_combo.currentIndexChanged.connect(lambda _=0: self._set("y_col", self.y_combo.currentData()))

        self.row_start = QSpinBox()
        self.row_start.setRange(1, 10_000_000)
        self.row_start.setValue(cfg.row_start)
        self.row_start.setFixedWidth(86)
        self.row_start.valueChanged.connect(lambda v: self._set("row_start", v))

        self.row_end = QSpinBox()
        self.row_end.setRange(1, 10_000_000)
        self.row_end.setValue(cfg.row_end)
        self.row_end.setFixedWidth(86)
        self.row_end.valueChanged.connect(lambda v: self._set("row_end", v))

        self.color_btn = QToolButton()
        self.color_btn.setIcon(_color_icon(cfg.color))
        self.color_btn.setToolTip("颜色（仅 16 种标准色）")
        self.color_btn.clicked.connect(self._pop_palette)

        self.shape_group = QButtonGroup(self)
        self.shape_group.setExclusive(True)
        shape_row = QHBoxLayout()
        shape_row.setSpacing(2)
        for shape in MarkerShape:
            btn = QPushButton(SHAPE_GLYPHS[shape.value])
            btn.setCheckable(True)
            btn.setFixedWidth(28)
            btn.setToolTip(shape.value)
            btn.setChecked(shape.value == cfg.shape)
            btn.clicked.connect(lambda _=False, s=shape.value: self._set("shape", s))
            self.shape_group.addButton(btn)
            shape_row.addWidget(btn)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(3, 20)
        self.size_spin.setValue(cfg.size)
        self.size_spin.setFixedWidth(50)
        self.size_spin.setSuffix("px")
        self.size_spin.valueChanged.connect(lambda v: self._set("size", v))

        # ---- 双行布局 ----
        line1 = QHBoxLayout()
        line1.setSpacing(6)
        line1.addWidget(self.visible_cb)
        line1.addWidget(QLabel("名称"))
        line1.addWidget(self.name_edit, 1)
        line1.addWidget(QLabel("X列"))
        line1.addWidget(self.x_combo)
        line1.addWidget(QLabel("Y列"))
        line1.addWidget(self.y_combo)

        line2 = QHBoxLayout()
        line2.setSpacing(6)
        line2.addWidget(QLabel("起始行"))
        line2.addWidget(self.row_start)
        line2.addWidget(QLabel("结束行"))
        line2.addWidget(self.row_end)
        line2.addWidget(self.color_btn)
        for i in range(shape_row.count()):
            w = shape_row.takeAt(0).widget()
            if w:
                line2.addWidget(w)
        line2.addWidget(QLabel("大小"))
        line2.addWidget(self.size_spin)
        line2.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(2)
        outer.addLayout(line1)
        outer.addLayout(line2)

    def _set(self, attr, value):
        setattr(self.cfg, attr, value)
        self.changed.emit()

    def _pop_palette(self):
        menu = QMenu(self)
        for name, hex_color in zip(EXCEL_SAFE_COLOR_NAMES, EXCEL_SAFE_COLORS):
            act = menu.addAction(_color_icon(hex_color), f"{name}  {hex_color}")
            act.triggered.connect(lambda _=False, c=hex_color: self._set_color(c))
        menu.exec(self.color_btn.mapToGlobal(self.color_btn.rect().bottomLeft()))

    def _set_color(self, color: str):
        self.cfg.color = color
        self.color_btn.setIcon(_color_icon(color))
        self.changed.emit()


class SeriesView(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: list[SeriesConfig] = []
        self._columns: list[tuple[str, str]] = []

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)

        add_btn = QPushButton("＋ 添加系列")
        add_btn.clicked.connect(self.add_series)

        layout = QVBoxLayout(self)
        layout.addLayout(self.rows_layout)
        layout.addWidget(add_btn)
        layout.addStretch(1)

    def set_series(self, series: list[SeriesConfig], columns: list[tuple[str, str]]):
        self._series = series
        self._columns = columns
        self._rebuild()

    def get_series(self) -> list[SeriesConfig]:
        return list(self._series)

    def add_series(self):
        last = self._series[-1] if self._series else None
        self._series.append(SeriesConfig(
            name=f"系列 {len(self._series) + 1}",
            x_col=(last.x_col if last else self._columns[0][0] if self._columns else "A"),
            y_col=(last.y_col if last else self._columns[1][0] if len(self._columns) > 1 else "B"),
            row_start=(last.row_end + 1 if last else 1),
            row_end=(last.row_end + 50 if last else 100),
            color=EXCEL_SAFE_COLORS[len(self._series) % 16],
            shape="circle", size=6,
        ))
        self._rebuild()
        self.changed.emit()

    def remove_series(self, index: int):
        if 0 <= index < len(self._series):
            del self._series[index]
            self._rebuild()
            self.changed.emit()

    def move_series(self, index: int, delta: int):
        j = index + delta
        if 0 <= j < len(self._series):
            self._series[index], self._series[j] = self._series[j], self._series[index]
            self._rebuild()

    def _rebuild(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for i, cfg in enumerate(self._series):
            row = SeriesRowWidget(cfg, self._columns)
            row.changed.connect(self.changed.emit)
            up = QPushButton("▲")
            up.setFixedWidth(30)
            up.setToolTip("上移")
            up.clicked.connect(lambda _=False, idx=i: self.move_series(idx, -1))
            down = QPushButton("▼")
            down.setFixedWidth(30)
            down.setToolTip("下移")
            down.clicked.connect(lambda _=False, idx=i: self.move_series(idx, 1))
            dele = QPushButton("🗑")
            dele.setFixedWidth(34)
            dele.setToolTip("删除系列")
            dele.clicked.connect(lambda _=False, idx=i: self.remove_series(idx))
            wrap = QWidget()
            hl = QHBoxLayout(wrap)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(row, 1)
            hl.addWidget(up)
            hl.addWidget(down)
            hl.addWidget(dele)
            self.rows_layout.addWidget(wrap)
