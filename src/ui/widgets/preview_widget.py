"""ECharts 图表预览（QWebEngineView，v3.2）。

- 每个系列按其行范围取数；>5000 点仅展示前 5000 点，导出全量。
- 轴刻度：步长（interval）+ 最小网格步长（minorSplitLine，5 小格/大格）。
- 散点连线（lineStyle）。
- dataZoom + toolbox；导出 PNG/SVG。
"""
from __future__ import annotations

import base64
import json
import os

from PySide6.QtCore import QEventLoop, QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.services.chart_builder import ChartOptions, SeriesConfig, check_limit_rules
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
__TOOLTIP_FN__
var opt = __OPTION__;
if (typeof tooltipFn !== 'undefined') { opt.tooltip.formatter = tooltipFn; }
var chart = echarts.init(document.getElementById('c'));
chart.setOption(opt);
window.addEventListener('resize', function(){ chart.resize(); });
</script></body></html>"""


def _split_number(major, minor):
    if major and minor:
        return max(1, round(major / minor))
    return 5


class PreviewWidget(QWebEngineView):
    renderReady = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._echarts_js = self._load_echarts()

    @staticmethod
    def _load_echarts() -> str:
        if os.path.isfile(_ASSET):
            with open(_ASSET, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def render(self, sl: SheetSlice, series_list: list[SeriesConfig], options: ChartOptions,
               banner_text: str = "") -> None:
        series_opts = []
        downsampled = False
        total_rows = sl.row_count

        visible_series = [s for s in series_list if getattr(s, "visible", True)]
        for cfg in visible_series:
            pts = numeric_series_points(sl, cfg.x_col, cfg.y_col, cfg.row_start, cfg.row_end)
            if len(pts) > DOWN_SAMPLE_LIMIT:
                downsampled = True
                pts = pts[:DOWN_SAMPLE_LIMIT]
            data = [[x, y] for x, y in pts]
            if options.connect_line:
                sopt = {
                    "name": cfg.name, "type": "line",
                    "showSymbol": True, "symbol": cfg.shape, "symbolSize": cfg.size,
                    "itemStyle": {"color": cfg.color},
                    "lineStyle": {"width": 1.5, "color": cfg.color},
                    "data": data,
                }
            else:
                sopt = {
                    "name": cfg.name, "type": "scatter",
                    "symbol": cfg.shape, "symbolSize": cfg.size,
                    "itemStyle": {"color": cfg.color},
                    "data": data,
                }
            series_opts.append(sopt)

        # 限值规则：画「允许区间」虚线框 + 标记超限点
        rules = options.rules or []
        for k, rule in enumerate(rules):
            box = [[rule.x_start, rule.y_min], [rule.x_end, rule.y_min],
                   [rule.x_end, rule.y_max], [rule.x_start, rule.y_max],
                   [rule.x_start, rule.y_min]]
            series_opts.append({
                "name": f"限值{k + 1}", "type": "line", "silent": True,
                "showSymbol": False,
                "lineStyle": {"color": "#d32f2f", "type": "dashed", "width": 1},
                "data": box,
            })
        exceeded = check_limit_rules(sl, rules)
        if exceeded:
            series_opts.append({
                "name": "超限点", "type": "scatter",
                "symbol": "circle", "symbolSize": 9,
                "itemStyle": {"color": "rgba(255,0,0,0.15)", "borderColor": "#d32f2f", "borderWidth": 2},
                "data": [[p["x"], p["y"]] for p in exceeded],
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
        if options.x_major_unit is not None:
            x_axis["interval"] = options.x_major_unit
        if options.y_major_unit is not None:
            y_axis["interval"] = options.y_major_unit
        x_axis["splitLine"] = {"show": bool(options.show_grid)}
        y_axis["splitLine"] = {"show": bool(options.show_grid)}
        if options.x_minor_unit is not None:
            x_axis["minorTick"] = {"show": True, "splitNumber": _split_number(options.x_major_unit, options.x_minor_unit)}
            x_axis["minorSplitLine"] = {"show": True}
        if options.y_minor_unit is not None:
            y_axis["minorTick"] = {"show": True, "splitNumber": _split_number(options.y_major_unit, options.y_minor_unit)}
            y_axis["minorSplitLine"] = {"show": True}

        option = {
            "title": {"text": options.title or "", "left": "center", "textStyle": {"fontSize": 14}},
            "tooltip": {"trigger": "item"},
            "legend": {"data": [s.name for s in visible_series],
                       "right": 10, "top": "middle", "orient": "vertical"},
            "grid": {"left": 60, "right": 160, "top": 60, "bottom": 60},
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
        if exceeded:
            n_y = sum(1 for p in exceeded if p["kind"] == "Y")
            n_x = sum(1 for p in exceeded if p["kind"] == "X")
            banner += (
                f'<div style="background:#fdecea;color:#b71c1c;border:1px solid #f5b8b8;'
                f'padding:6px 10px;font-size:12px;border-radius:4px;margin:6px;">'
                f'⚠️ 检测到 <b>{len(exceeded)}</b> 个超限点（X 超限 {n_x} 个 · Y 超限 {n_y} 个）'
                f'，导出时超限单元格将标红</div>'
            )
        if downsampled or banner_text:
            banner += (
                f'<div style="background:#fff3e0;color:#8a5a12;border:1px solid #f5d9a8;'
                f'padding:6px 10px;font-size:12px;border-radius:4px;margin:6px;">'
                f'⚠️ 预览仅展示前 {DOWN_SAMPLE_LIMIT:,} 个数据点，<b>导出时将包含全部数据</b>'
                f'（共 {total_rows:,} 行）</div>'
            )

        html = _HTML_TEMPLATE
        html = html.replace("__ECHARTS__", self._echarts_js)
        html = html.replace("__OPTION__", json.dumps(option, ensure_ascii=False))
        # tooltip formatter 作为原始 JS 函数注入（不经过 json.dumps）
        x_label = (options.x_label or "X").replace("'", "\\'")
        y_label = (options.y_label or "Y").replace("'", "\\'")
        tooltip_fn = (
            f"function tooltipFn(p){{"
            f"return '<b>'+p.seriesName+'</b><br/>'"
            f"+'{x_label} : '+p.value[0]"
            f"+'<br/>{y_label} : '+p.value[1];}}"
        )
        html = html.replace("__TOOLTIP_FN__", tooltip_fn)
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
