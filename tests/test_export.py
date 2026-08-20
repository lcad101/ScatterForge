"""导出服务测试（冻结规范第 7 章：raw data + Chart View + 覆盖备份）。"""
import glob
import os

import openpyxl
from openpyxl import load_workbook

from src.services.chart_builder import ChartOptions, SeriesConfig
from src.services.excel_export_service import ExcelExportService
from src.services.excel_handler import CHART_VIEW_SHEET, RAW_DATA_SHEET, ExcelHandler


def make_slice(tmp_path):
    p = tmp_path / "src.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["X", "Y"])
    for i in range(1, 51):
        ws.append([i, i * 1.5])
    wb.save(p)
    return ExcelHandler().read_slice(str(p), 1, 50, "A", "B")


def test_export_two_sheets(tmp_path):
    sl = make_slice(tmp_path)
    series = [SeriesConfig("系列1", "A", "B", "#FF0000", "circle", 8),
              SeriesConfig("系列2", "A", "B", "#0000FF", "diamond", 6)]
    opts = ChartOptions(title="测试散点图", x_label="X", y_label="Y", show_grid=True)
    out = tmp_path / "out.xlsx"
    ExcelExportService().export(sl, series, opts, str(out))

    wb = load_workbook(str(out))
    assert wb.sheetnames == [RAW_DATA_SHEET, CHART_VIEW_SHEET]
    ws_data = wb[RAW_DATA_SHEET]
    assert ws_data.max_row == 51  # 表头 + 50 数据行
    assert ws_data.cell(1, 1).value == "X"
    assert ws_data.cell(51, 2).value == 75.0  # 50 * 1.5
    chart_sheet = wb[CHART_VIEW_SHEET]
    assert len(chart_sheet._charts) == 1


def test_overwrite_with_backup_and_cleanup(tmp_path):
    sl = make_slice(tmp_path)
    series = [SeriesConfig("s", "A", "B", "#00B050", "square", 8)]
    opts = ChartOptions(title="t", show_grid=False)
    out = tmp_path / "out.xlsx"
    svc = ExcelExportService()
    svc.export(sl, series, opts, str(out))
    # 再次覆盖导出
    svc2 = ExcelExportService()
    svc2.export(sl, series, opts, str(out))
    assert os.path.isfile(str(out))
    # 无残留 .tmp / .backup 文件
    assert not glob.glob(str(tmp_path / "*.tmp"))
    assert not glob.glob(str(tmp_path / "*.backup_*"))


def test_cancel_export(tmp_path):
    sl = make_slice(tmp_path)
    series = [SeriesConfig("s", "A", "B", "#FF0000", "circle", 8)]
    opts = ChartOptions(title="t")
    svc = ExcelExportService()
    svc.cancel()  # 立即取消
    from src.core.exceptions import OperationCancelledException
    import pytest
    out = tmp_path / "out.xlsx"
    with pytest.raises(OperationCancelledException):
        svc.export(sl, series, opts, str(out))
    assert not os.path.isfile(str(out))
