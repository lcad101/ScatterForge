"""ECharts 图表预览（QWebEngineView）。

冻结规范第 2/6/14 章：
- 降采样契约：数据 > 5,000 行仅展示前 5,000 点，导出仍全量写入。
- 缩放平移：启用 dataZoom（inside + slider）与 toolbox（缩放/复位/保存图片）。
- 导出图片：支持 PNG / SVG（Q4）。
"""
from __future__ import annotations

import base64
import json
import os

from PySide6.QtCore import QEventLoop, QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.services.chart_builder import ChartOptions, SeriesConfig
from src.services.excel_handler import SheetSlice, numeric_series_points

DOWN_SAMPLE_LIMIT = 5000

_ASSET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "assets", "echarts.min.js")

_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>html,body{margin:0;width:100%;height:100%;}#c{width:100%;height:100%;}</style>
</head><body><div id="c"></div>
<script>__ECHARTS__</script>
<script>
var chart = echarts.init(document.getElementById('c'));
chart.setOption(__OPTION__);
window.addEventListener('resize', function(){ chart.resize(); });
</script></body></html>"""


class PreviewWidget(QWebEngineView):
    renderReady = Signal(int)  # 渲染数据点数（降采样后）

    def __init__(self, parent=None):
        super().__init__(parent)
        self._echarts_js = self._load_echarts()
        self._data_rows = 0

    @staticmethod
    def _load_echarts() -> str:
        if os.path.isfile(_ASSET):
            with open(_ASSET, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    # ---------------- 渲染 ----------------
    def render(self, sl: SheetSlice, series_list: list[SeriesConfig], options: ChartOptions,
               banner_text: str = "") -> None:
        series_opts = []
        downsampled = False
        total_rows = sl.row_count
        self._data_rows = total_rows

        for cfg in series_list:
            pts = numeric_series_points(sl, cfg.x_col, cfg.y_col)
            if len(pts) > DOWN_SAMPLE_LIMIT:
                downsampled = True
                pts = pts[:DOWN_SAMPLE_LIMIT]
            series_opts.append({
                "name": cfg.name,
                "type": "scatter",
                "symbol": cfg.shape,
                "symbolSize": cfg.size,
                "itemStyle": {"color": cfg.color},
                "data": [[x, y] for x, y in pts],
            })

        x_axis = {"type": "value", "scale": True, "name": options.x_label or ""}
        y_axis = {"type": "value", "scale": True, "name": options.y_label or ""}
        if options.x_min is not None:
            x_axis["min"] = options.x_min
        if options.x_max is not None:
            x_axis["max"] = options.x_max
        if options.y_min is not None:
            y_axis["min"] = options.y_min
        if options.y_max is not None:
            y_axis["max"] = options.y_max
        if not options.show_grid:
            x_axis["splitLine"] = {"show": False}
            y_axis["splitLine"] = {"show": False}

        option = {
            "title": {"text": options.title or "", "left": "center", "textStyle": {"fontSize": 14}},
            "tooltip": {"trigger": "item"},
            "legend": {"data": [s.name for s in series_list], "bottom": 0},
            "grid": {"left": 60, "right": 40, "top": 60, "bottom": 60},
            "xAxis": x_axis,
            "yAxis": y_axis,
            "dataZoom": [{"type": "inside"}, {"type": "slider", "bottom": 28}],
            "toolbox": {
                "right": 10, "top": 10,
                "feature": {
                    "dataZoom": {"title": {"zoom": "区域缩放", "back": "还原缩放"}},
                    "restore": {"title": "复位"},
                    "saveAsImage": {"title": "保存图片"},
                },
            },
            "series": series_opts,
        }

        banner = ""
        if downsampled or banner_text:
            banner = (
                f'<div style="background:#fff3e0;color:#8a5a12;border:1px solid #f5d9a8;'
                f'padding:6px 10px;font-size:12px;border-radius:4px;margin:6px;">'
                f'⚠️ 预览仅展示前 {DOWN_SAMPLE_LIMIT:,} 个数据点，<b>导出时将包含全部数据</b>'
                f'（共 {total_rows:,} 行）</div>'
            )

        html = _HTML_TEMPLATE
        html = html.replace("__ECHARTS__", self._echarts_js)
        html = html.replace("__OPTION__", json.dumps(option, ensure_ascii=False))
        if banner:
            html = html.replace("<div id=\"c\">", banner + '<div id="c">')
        self.setHtml(html, QUrl("about:blank"))
        self.renderReady.emit(min(total_rows, DOWN_SAMPLE_LIMIT))

    # ---------------- JS 桥接 ----------------
    def _run_js(self, js: str):
        loop = QEventLoop()
        result = {}

        def cb(value):
            result["v"] = value
            loop.quit()

        self.page().runJavaScript(js, cb)
        loop.exec()
        return result.get("v")

    def export_image(self, fmt: str, target_path: str, width: int, height: int) -> None:
        """导出当前预览为 PNG 或 SVG。"""
        if not self._echarts_js:
            raise RuntimeError("ECharts 库未加载")

        if fmt.upper() == "PNG":
            chart_w = self._run_js("chart ? chart.getWidth() : 0") or 0
            ratio = max(1, round(width / chart_w)) if chart_w else 2
            data_url = self._run_js(
                f"chart.getDataURL({{type:'png', pixelRatio:{ratio}, backgroundColor:'#ffffff'}})"
            )
            if not data_url or "base64," not in data_url:
                raise RuntimeError("PNG 导出失败")
            raw = base64.b64decode(data_url.split("base64,", 1)[1])
            with open(target_path, "wb") as f:
                f.write(raw)
        else:  # SVG
            svg = self._run_js("chart.renderToSVGString()")
            if not svg:
                raise RuntimeError("SVG 导出失败")
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(svg)
