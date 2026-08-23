"""原生散点图构建（openpyxl ScatterChart，v3.2）。

- 每个系列绑定 raw data 页对应列 + 自己的行范围（真实 Excel 行号）。
- 轴刻度：步长（majorUnit）+ 最小网格步长（minorUnit）+ 大/小网格线。
- 散点连线（connect_line）：连线（markers + lines）或纯散点。
- 仅 16 种标准色 + 4 种形状，直接透传。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from openpyxl.chart import Reference, ScatterChart
from openpyxl.chart import Series as ChartSeries
from openpyxl.chart.axis import ChartLines
from openpyxl.worksheet.worksheet import Worksheet

from src.core.stoppable import IStoppable
from src.models.validators import col_to_index


@dataclass
class SeriesConfig:
    """系列配置（每个系列必填行范围）。"""
    name: str
    x_col: str
    y_col: str
    row_start: int                    # 必填：真实 Excel 起始行
    row_end: int                      # 必填：真实 Excel 结束行
    color: str = "#FF0000"            # 16 种标准色之一
    shape: str = "circle"             # circle/diamond/square/triangle
    size: int = 8
    visible: bool = True              # 预览中是否显示该系列


@dataclass
class LimitRule:
    """条件限值规则：X 列取值在 [x_start, x_end] 内时，Y 列须在 [y_min, y_max] 内。"""
    x_col: str = "A"                   # X 列（如电压列）
    y_col: str = "B"                   # Y 列（如功率列）
    x_start: float = 0.0               # X 范围下限
    x_end: float = 0.0                 # X 范围上限
    y_min: float = 0.0                 # Y 下限
    y_max: float = 0.0                 # Y 上限


@dataclass
class ChartOptions:
    """图表元数据。"""
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    y_min: Optional[float] = None
    y_max: Optional[float] = None
    x_major_unit: Optional[float] = None   # X 步长（主要刻度单位）
    x_minor_unit: Optional[float] = None   # X 最小网格步长（次要刻度单位）
    y_major_unit: Optional[float] = None
    y_minor_unit: Optional[float] = None
    show_grid: bool = True
    connect_line: bool = True              # 散点连线
    rules: list = field(default_factory=list)   # list[LimitRule]，条件限值规则


def check_limit_rules(sl, rules: list) -> list[dict]:
    """检测超限点：返回 [{row(真实行号), x, y, kind('Y'|'X'), lo, hi}]。

    - kind='Y'：X 落在某规则 [x_start,x_end] 内，但 Y 超出 [y_min,y_max]。
    - kind='X'：X 不在任何规则的 [x_start,x_end] 区间内（X 超限）。
    sl: SheetSlice；rules: list[LimitRule]（通常各规则共用同一 X/Y 列）。
    """
    from src.models.validators import col_to_index
    exceeded: list[dict] = []
    if not rules:
        return exceeded
    xi = col_to_index(rules[0].x_col) - sl.start_col
    yi = col_to_index(rules[0].y_col) - sl.start_col
    ranges = [(r.x_start, r.x_end, r.y_min, r.y_max) for r in rules]
    for i, row in enumerate(sl.rows):
        if xi < 0 or yi < 0 or xi >= len(row) or yi >= len(row):
            continue
        try:
            x = float(row[xi])
            y = float(row[yi])
        except (TypeError, ValueError):
            continue
        for (xs, xe, ylo, yhi) in ranges:
            if xs <= x <= xe:
                if y < ylo or y > yhi:
                    exceeded.append({"row": sl.start_row + i, "x": x, "y": y,
                                     "kind": "Y", "lo": ylo, "hi": yhi})
                break
        else:
            # X 不在任何规则区间 → X 超限
            exceeded.append({"row": sl.start_row + i, "x": x, "y": y,
                             "kind": "X", "lo": None, "hi": None})
    return exceeded


class ChartBuilder(IStoppable):
    """从 raw data 工作表构建 ScatterChart。"""

    def __init__(self) -> None:
        super().__init__()

    def build(self, ws_data: Worksheet, series_list: list[SeriesConfig],
              options: ChartOptions) -> ScatterChart:
        chart = ScatterChart()
        chart.title = options.title or ""
        chart.x_axis.title = options.x_label or ""
        chart.y_axis.title = options.y_label or ""

        if options.x_min is not None:
            chart.x_axis.scaling.min = options.x_min
        if options.x_max is not None:
            chart.x_axis.scaling.max = options.x_max
        if options.y_min is not None:
            chart.y_axis.scaling.min = options.y_min
        if options.y_max is not None:
            chart.y_axis.scaling.max = options.y_max

        # 刻度：步长（主要）+ 最小网格步长（次要）
        if options.x_major_unit is not None:
            chart.x_axis.majorUnit = options.x_major_unit
        if options.x_minor_unit is not None:
            chart.x_axis.minorUnit = options.x_minor_unit
        if options.y_major_unit is not None:
            chart.y_axis.majorUnit = options.y_major_unit
        if options.y_minor_unit is not None:
            chart.y_axis.minorUnit = options.y_minor_unit

        if options.show_grid:
            chart.x_axis.majorGridlines = ChartLines()
            chart.y_axis.majorGridlines = ChartLines()
            if options.x_minor_unit is not None:
                chart.x_axis.minorGridlines = ChartLines()
            if options.y_minor_unit is not None:
                chart.y_axis.minorGridlines = ChartLines()

        chart.legend.position = "r"

        for cfg in series_list:
            if self.should_cancel():
                from src.core.exceptions import OperationCancelledException
                raise OperationCancelledException("用户取消构建图表")

            x_idx = col_to_index(cfg.x_col)
            y_idx = col_to_index(cfg.y_col)
            # 该系列自己的行范围（真实 Excel 行号）
            xref = Reference(ws_data, min_col=x_idx, min_row=cfg.row_start, max_row=cfg.row_end)
            yref = Reference(ws_data, min_col=y_idx, min_row=cfg.row_start, max_row=cfg.row_end)
            series = ChartSeries(yref, xref, title=cfg.name)

            series.marker.symbol = cfg.shape
            series.marker.size = cfg.size
            a_rgb = cfg.color.lstrip("#").upper()
            series.marker.graphicalProperties.solidFill = a_rgb

            if options.connect_line:
                # 散点连线：markers + lines
                series.graphicalProperties.line.solidFill = a_rgb
                series.graphicalProperties.line.width = 20000  # 1.5pt
            else:
                # 纯散点：不连线
                series.graphicalProperties.line.noFill = True

            chart.series.append(series)

        return chart
