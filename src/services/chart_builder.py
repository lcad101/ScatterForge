"""原生散点图构建（openpyxl ScatterChart）。

冻结规范第 2/6 章：绑定 raw data 页的对应列；仅 16 种标准色 + 4 种形状，直接透传。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from openpyxl.chart import Reference, ScatterChart
from openpyxl.chart import Series as ChartSeries
from openpyxl.chart.axis import ChartLines
from openpyxl.worksheet.worksheet import Worksheet

from src.core.stoppable import IStoppable
from src.models.validators import col_to_index


@dataclass
class SeriesConfig:
    """系列配置（与 ORM Series 解耦的轻量结构）。"""
    name: str
    x_col: str
    y_col: str
    color: str = "#FF0000"      # 16 种标准色之一
    shape: str = "circle"       # circle/diamond/square/triangle
    size: int = 8


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
    show_grid: bool = True


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

        if options.show_grid:
            chart.x_axis.majorGridlines = ChartLines()
            chart.y_axis.majorGridlines = ChartLines()

        chart.legend.position = "r"

        max_row = max(ws_data.max_row, 2)
        for cfg in series_list:
            if self.should_cancel():
                from src.core.exceptions import OperationCancelledException
                raise OperationCancelledException("用户取消构建图表")

            x_idx = col_to_index(cfg.x_col)
            y_idx = col_to_index(cfg.y_col)
            xref = Reference(ws_data, min_col=x_idx, min_row=2, max_row=max_row)
            yref = Reference(ws_data, min_col=y_idx, min_row=2, max_row=max_row)
            series = ChartSeries(yref, xref, title=cfg.name)

            # 形状（4 选 1）
            series.marker.symbol = cfg.shape
            series.marker.size = cfg.size
            # 颜色（aRGB，去掉 #）
            a_rgb = cfg.color.lstrip("#").upper()
            series.marker.graphicalProperties.solidFill = a_rgb
            # 散点：仅标记点，不连线
            series.graphicalProperties.line.noFill = True

            chart.series.append(series)

        return chart
