"""图表选项页（v3.2）：标题/轴标签/范围/步长/最小网格步长/网格/散点连线/条件限值规则。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from src.services.chart_builder import ChartOptions, LimitRule


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
        self.chart_name = QLineEdit()
        self.title = QLineEdit()
        self.x_label = QLineEdit()
        self.y_label = QLineEdit()
        self.x_min = QLineEdit()
        self.x_max = QLineEdit()
        self.y_min = QLineEdit()
        self.y_max = QLineEdit()
        self.x_major = QLineEdit()
        self.x_minor = QLineEdit()
        self.y_major = QLineEdit()
        self.y_minor = QLineEdit()
        self.show_grid = QCheckBox("显示网格线")
        self.show_grid.setChecked(True)
        self.connect_line = QCheckBox("散点连线（折线连接）")
        self.connect_line.setChecked(True)

        for w in (self.chart_name, self.title, self.x_label, self.y_label,
                  self.x_min, self.x_max, self.y_min, self.y_max,
                  self.x_major, self.x_minor, self.y_major, self.y_minor):
            w.textChanged.connect(lambda *_: self.changed.emit())
        for w in (self.x_min, self.x_max, self.y_min, self.y_max,
                  self.x_major, self.x_minor, self.y_major, self.y_minor):
            w.setPlaceholderText("自动")
        self.show_grid.toggled.connect(lambda *_: self.changed.emit())
        self.connect_line.toggled.connect(lambda *_: self.changed.emit())

        form = QFormLayout()
        form.addRow("图表名（= Sheet 名）", self.chart_name)
        form.addRow("图表标题", self.title)
        form.addRow("X 轴标签", self.x_label)
        form.addRow("Y 轴标签", self.y_label)
        form.addRow("X 轴范围", self._row(self.x_min, self.x_max))
        form.addRow("Y 轴范围", self._row(self.y_min, self.y_max))
        form.addRow("X 轴步长（主要刻度）", self.x_major)
        form.addRow("X 最小网格步长（次要刻度）", self.x_minor)
        form.addRow("Y 轴步长（主要刻度）", self.y_major)
        form.addRow("Y 最小网格步长（次要刻度）", self.y_minor)
        form.addRow("", self.show_grid)
        form.addRow("", self.connect_line)

        # 条件限值规则（X 区间 → Y 上下限；X 超限 + Y 超限）
        self._columns: list[tuple[str, str]] = []
        self._rules: list[LimitRule] = []
        self.rules_layout = QVBoxLayout()
        self.rules_layout.setSpacing(4)
        self.add_rule_btn = QPushButton("＋ 添加限值规则")
        self.add_rule_btn.clicked.connect(self.add_rule)

        hint = QLabel("💡 限值规则：X 列取值在 [X起, X止] 内时，Y 列须在 [Y小, Y大] 内；"
                      "X 不在任何区间 → X 超限，Y 越界 → Y 超限。导出时超限单元格标红。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8a6d1a;background:#fff8e6;border:1px solid #f3dfa8;padding:6px;border-radius:4px;")

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("限值规则"))
        layout.addLayout(self.rules_layout)
        layout.addWidget(self.add_rule_btn)
        layout.addWidget(hint)
        layout.addStretch(1)

    @staticmethod
    def _row(w1, w2):
        r = QHBoxLayout()
        r.addWidget(w1)
        r.addWidget(w2)
        return r

    def set_columns(self, columns: list[tuple[str, str]]):
        self._columns = columns or [("A", "A"), ("B", "B")]
        self._rebuild_rules()

    def _combo(self, current: str):
        cb = QComboBox()
        for letter, header in self._columns:
            cb.addItem(letter, letter)
        idx = cb.findText(current)
        if idx >= 0:
            cb.setCurrentIndex(idx)
        return cb

    def _rebuild_rules(self):
        while self.rules_layout.count():
            item = self.rules_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for i, rule in enumerate(self._rules):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            xcol = self._combo(rule.x_col)
            ycol = self._combo(rule.y_col)
            xs = QLineEdit(str(rule.x_start))
            xe = QLineEdit(str(rule.x_end))
            ylo = QLineEdit(str(rule.y_min))
            yhi = QLineEdit(str(rule.y_max))
            xcol.currentTextChanged.connect(lambda t, r=rule: self._set_rule(r, "x_col", t))
            ycol.currentTextChanged.connect(lambda t, r=rule: self._set_rule(r, "y_col", t))
            xs.textChanged.connect(lambda t, r=rule: self._set_rule_float(r, "x_start", t))
            xe.textChanged.connect(lambda t, r=rule: self._set_rule_float(r, "x_end", t))
            ylo.textChanged.connect(lambda t, r=rule: self._set_rule_float(r, "y_min", t))
            yhi.textChanged.connect(lambda t, r=rule: self._set_rule_float(r, "y_max", t))
            dele = QPushButton("🗑")
            dele.setFixedWidth(32)
            dele.clicked.connect(lambda _=False, idx=i: self.remove_rule(idx))
            h.addWidget(QLabel("X列"))
            h.addWidget(xcol)
            h.addWidget(QLabel("X起"))
            h.addWidget(xs)
            h.addWidget(QLabel("X止"))
            h.addWidget(xe)
            h.addWidget(QLabel("Y列"))
            h.addWidget(ycol)
            h.addWidget(QLabel("Y小"))
            h.addWidget(ylo)
            h.addWidget(QLabel("Y大"))
            h.addWidget(yhi)
            h.addWidget(dele)
            self.rules_layout.addWidget(row)

    def _set_rule(self, rule, attr, val):
        setattr(rule, attr, val)
        self.changed.emit()

    def _set_rule_float(self, rule, attr, text):
        v = _parse_float(text)
        if v is not None:
            setattr(rule, attr, v)
            self.changed.emit()

    def add_rule(self):
        self._rules.append(LimitRule(x_col=self._columns[0][0], y_col=self._columns[1][0] if len(self._columns) > 1 else "B",
                                     x_start=0.0, x_end=0.0, y_min=0.0, y_max=0.0))
        self._rebuild_rules()
        self.changed.emit()

    def remove_rule(self, index):
        if 0 <= index < len(self._rules):
            del self._rules[index]
            self._rebuild_rules()
            self.changed.emit()

    def get_options(self) -> ChartOptions:
        return ChartOptions(
            title=self.title.text().strip() or None,
            x_label=self.x_label.text().strip() or None,
            y_label=self.y_label.text().strip() or None,
            x_min=_parse_float(self.x_min.text()),
            x_max=_parse_float(self.x_max.text()),
            y_min=_parse_float(self.y_min.text()),
            y_max=_parse_float(self.y_max.text()),
            x_major_unit=_parse_float(self.x_major.text()),
            x_minor_unit=_parse_float(self.x_minor.text()),
            y_major_unit=_parse_float(self.y_major.text()),
            y_minor_unit=_parse_float(self.y_minor.text()),
            show_grid=self.show_grid.isChecked(),
            connect_line=self.connect_line.isChecked(),
            rules=[LimitRule(x_col=r.x_col, y_col=r.y_col, x_start=r.x_start, x_end=r.x_end,
                             y_min=r.y_min, y_max=r.y_max) for r in self._rules],
        )

    def get_chart_name(self) -> str:
        return self.chart_name.text().strip() or "图表"

    def set_options(self, options: ChartOptions):
        self.title.setText(options.title or "")
        self.x_label.setText(options.x_label or "")
        self.y_label.setText(options.y_label or "")
        self.x_min.setText("" if options.x_min is None else str(options.x_min))
        self.x_max.setText("" if options.x_max is None else str(options.x_max))
        self.y_min.setText("" if options.y_min is None else str(options.y_min))
        self.y_max.setText("" if options.y_max is None else str(options.y_max))
        self.x_major.setText("" if options.x_major_unit is None else str(options.x_major_unit))
        self.x_minor.setText("" if options.x_minor_unit is None else str(options.x_minor_unit))
        self.y_major.setText("" if options.y_major_unit is None else str(options.y_major_unit))
        self.y_minor.setText("" if options.y_minor_unit is None else str(options.y_minor_unit))
        self.show_grid.setChecked(options.show_grid)
        self.connect_line.setChecked(options.connect_line)
        self._rules = [LimitRule(x_col=r.x_col, y_col=r.y_col, x_start=r.x_start, x_end=r.x_end,
                                 y_min=r.y_min, y_max=r.y_max) for r in (options.rules or [])]
        self._rebuild_rules()
