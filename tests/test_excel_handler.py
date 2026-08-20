"""ExcelHandler 列区间流式读取测试（冻结规范：read_only 只解析列区间）。"""
import openpyxl
import pytest

from src.core.exceptions import FileMissingException
from src.services.excel_handler import ExcelHandler, numeric_series_points


def make_sample(path, nrows=20, ncols=4):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["X", "Y", "Label", "Z"])  # 表头第 1 行
    for i in range(1, nrows + 1):
        ws.append([i, i * 2.0, f"row-{i}", i * 3])
    wb.save(path)
    return path


def test_read_slice_full(tmp_path):
    p = make_sample(tmp_path / "s.xlsx", nrows=20)
    sl = ExcelHandler().read_slice(str(p), start_row=1, end_row=20, start_col="A", end_col="D")
    assert sl.row_count == 20
    assert sl.headers == ["X", "Y", "Label", "Z"]
    assert sl.rows[0] == [1, 2.0, "row-1", 3]
    assert sl.rows[19][3] == 60  # 20 * 3


def test_read_slice_single_row(tmp_path):
    """end_row=None → 仅取起始行这一行。"""
    p = make_sample(tmp_path / "s.xlsx", nrows=20)
    sl = ExcelHandler().read_slice(str(p), start_row=3, end_row=None, start_col="A", end_col="D")
    assert sl.row_count == 1
    assert sl.rows[0][1] == 6.0  # 数据行 3 的 Y = 3*2


def test_read_slice_column_range(tmp_path):
    """只解析 B~C 列区间。"""
    p = make_sample(tmp_path / "s.xlsx", nrows=20)
    sl = ExcelHandler().read_slice(str(p), start_row=1, end_row=5, start_col="B", end_col="C")
    assert sl.start_col == 2 and sl.end_col == 3
    assert sl.headers == ["Y", "Label"]
    assert sl.rows[0] == [2.0, "row-1"]


def test_numeric_series_points(tmp_path):
    p = make_sample(tmp_path / "s.xlsx", nrows=20)
    sl = ExcelHandler().read_slice(str(p), start_row=1, end_row=20, start_col="A", end_col="D")
    pts = numeric_series_points(sl, "A", "B")
    assert len(pts) == 20
    assert pts[0] == (1.0, 2.0)


def test_file_missing(tmp_path):
    with pytest.raises(FileMissingException):
        ExcelHandler().read_slice(str(tmp_path / "nope.xlsx"), 1, 1, "A", "A")
