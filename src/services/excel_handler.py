"""Excel 流式读取（冻结规范第 2/3 章）。

架构强制契约：
- 在 read_only 模式下，只解析 min_col~max_col 列区间，禁止全量扫描（性能提升 5-10 倍）。
- 列名解析：iter_rows(min_col, max_col, max_row=1) 仅读标题行。
- 实现 IStoppable，供导入流程取消。

行列契约（本实现约定，供 UI 与文档一致）：
- 第 1 行为表头（标题行），单独读取，不写入数据。
- start_row / end_row 为「数据行号」（1 基，不含表头）：数据行 k = Excel 行 k+1。
- end_row 为空（None）→ 仅取 start_row 一行。
- end_col 为空（None）→ 仅取 start_col 一列。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from openpyxl import load_workbook

from src.core.exceptions import FileMissingException, OperationCancelledException
from src.core.stoppable import IStoppable
from src.models.validators import col_to_index, index_to_col

RAW_DATA_SHEET = "raw data"
CHART_VIEW_SHEET = "Chart View"


@dataclass
class SheetSlice:
    """行列切片结果。rows 与 headers 均按 start_col..end_col 顺序对齐。"""
    start_col: int  # 1 基列索引（源文件列位置，原样保留）
    end_col: int
    headers: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)

    @property
    def column_letters(self) -> list[str]:
        return [index_to_col(i) for i in range(self.start_col, self.end_col + 1)]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _norm_col(col: str | int) -> int:
    return col_to_index(col) if isinstance(col, str) else int(col)


class ExcelHandler(IStoppable):
    """按列区间流式读取 Excel。"""

    def __init__(self) -> None:
        super().__init__()

    # ---------------- 源文件读取 ----------------
    def read_slice(
        self,
        path: str,
        start_row: int,
        end_row: Optional[int],
        start_col: str | int,
        end_col: Optional[str | int],
        sheet: Optional[str] = None,
    ) -> SheetSlice:
        """读取指定行列切片（含表头）。"""
        if not path or not _exists(path):
            raise FileMissingException(f"文件不存在：{path}")

        sc = _norm_col(start_col)
        ec = sc if end_col is None else _norm_col(end_col)
        if ec < sc:
            ec = sc

        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb[sheet] if sheet else wb.active
            max_row = ws.max_row

            # 表头：第 1 行
            headers = self._read_headers(ws, sc, ec)

            # 数据行：Excel 行 = start_row + 1 .. end_row + 1（表头占第 1 行）
            excel_first = start_row + 1
            if end_row is None:
                excel_last = excel_first
            else:
                excel_last = min(end_row + 1, max_row)
            if excel_last < excel_first:
                excel_last = excel_first

            rows: list[list[Any]] = []
            for ri, row in enumerate(ws.iter_rows(min_row=excel_first, max_row=excel_last,
                                                  min_col=sc, max_col=ec, values_only=True)):
                if self.should_cancel():
                    raise OperationCancelledException("用户取消导入")
                if ri % 1000 == 0 and self.should_cancel():
                    raise OperationCancelledException("用户取消导入")
                rows.append(list(row))
            return SheetSlice(start_col=sc, end_col=ec, headers=headers, rows=rows)
        finally:
            wb.close()

    def read_headers(self, path: str, start_col: str | int, end_col: Optional[str | int],
                     sheet: Optional[str] = None) -> list[str]:
        sc = _norm_col(start_col)
        ec = sc if end_col is None else _norm_col(end_col)
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb[sheet] if sheet else wb.active
            return self._read_headers(ws, sc, ec)
        finally:
            wb.close()

    def count_data_rows(self, path: str, sheet: Optional[str] = None) -> int:
        """数据行数（不含表头）。"""
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb[sheet] if sheet else wb.active
            return max(0, ws.max_row - 1)
        finally:
            wb.close()

    # ---------------- 从已生成文件的 raw data 页重新读取（场景 2） ----------------
    def read_raw_data_sheet(
        self,
        path: str,
        start_row: int,
        end_row: Optional[int],
        start_col: str | int,
        end_col: Optional[str | int],
    ) -> SheetSlice:
        """读取本项目导出文件中的 raw data 页（用于再次编辑）。"""
        return self.read_slice(path, start_row, end_row, start_col, end_col, sheet=RAW_DATA_SHEET)

    @staticmethod
    def _read_headers(ws, sc: int, ec: int) -> list[str]:
        headers: list[str] = []
        for row in ws.iter_rows(min_row=1, max_row=1, min_col=sc, max_col=ec, values_only=True):
            for c, val in enumerate(row, start=sc):
                headers.append(str(val) if val is not None and str(val) != "" else index_to_col(c))
        # 兜底补齐
        while len(headers) < (ec - sc + 1):
            headers.append(index_to_col(sc + len(headers)))
        return headers


def numeric_series_points(sl: SheetSlice, x_col: str, y_col: str) -> list[tuple[float, float]]:
    """从切片中抽取 (x, y) 数值点（跳过非数值单元格）。"""
    xi = col_to_index(x_col) - sl.start_col
    yi = col_to_index(y_col) - sl.start_col
    pts: list[tuple[float, float]] = []
    for row in sl.rows:
        if xi < 0 or yi < 0 or xi >= len(row) or yi >= len(row):
            continue
        try:
            x = float(row[xi])
            y = float(row[yi])
        except (TypeError, ValueError):
            continue
        pts.append((x, y))
    return pts


def _exists(path: str) -> bool:
    import os
    return os.path.isfile(path)
