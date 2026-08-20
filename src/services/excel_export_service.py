"""导出服务：生成全新 Excel 文件（raw data + Chart View 两页），覆盖式写入。

冻结规范第 7 章（方案 A）：
- 内存新建 Workbook → raw data 页写切片数据 → Chart View 页插入原生散点图。
- 写前备份 → 写 .tmp → 校验 → 替换 → 删除备份。
- 取消/异常回滚三要素：删除临时文件、恢复备份（覆盖场景）、由调用方回滚事务。
- 禁止修改原用户文件（本服务只写目标导出文件）。
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Callable, Optional

from openpyxl import Workbook, load_workbook

from src.core.exceptions import OperationCancelledException, OperationFailedException
from src.core.stoppable import IStoppable
from src.services.chart_builder import ChartBuilder, ChartOptions, SeriesConfig
from src.services.excel_handler import CHART_VIEW_SHEET, RAW_DATA_SHEET, SheetSlice

ProgressCb = Callable[[int], None]


class ExcelExportService(IStoppable):
    """生成 + 保存导出文件。"""

    def __init__(self) -> None:
        super().__init__()

    def export(
        self,
        sl: SheetSlice,
        series_list: list[SeriesConfig],
        options: ChartOptions,
        target_path: str,
        progress_cb: Optional[ProgressCb] = None,
    ) -> str:
        """完整导出流程，返回最终文件路径。"""
        wb = self.build_workbook(sl, series_list, options, progress_cb)
        self.save_workbook(wb, target_path)
        if progress_cb:
            progress_cb(100)
        return target_path

    def build_workbook(
        self,
        sl: SheetSlice,
        series_list: list[SeriesConfig],
        options: ChartOptions,
        progress_cb: Optional[ProgressCb] = None,
    ) -> Workbook:
        wb = Workbook()
        ws_data = wb.active
        ws_data.title = RAW_DATA_SHEET

        # 表头（保持源列位置，图表按原列字母引用）
        for i, header in enumerate(sl.headers):
            ws_data.cell(row=1, column=sl.start_col + i, value=header)

        # 数据行（每 1000 行检查一次取消 + 上报进度）
        total = max(len(sl.rows), 1)
        for ri, row in enumerate(sl.rows):
            if ri % 1000 == 0:
                if self.should_cancel():
                    raise OperationCancelledException("用户取消导出")
                if progress_cb:
                    progress_cb(int(ri / total * 90))
            excel_row = ri + 2
            for i, val in enumerate(row):
                ws_data.cell(row=excel_row, column=sl.start_col + i, value=val)

        # 图表页
        ws_chart = wb.create_sheet(CHART_VIEW_SHEET)
        chart = ChartBuilder().build(ws_data, series_list, options)
        ws_chart.add_chart(chart, "A1")
        return wb

    def save_workbook(self, workbook: Workbook, target_path: str) -> None:
        """写前备份 → .tmp → 校验 → 替换 → 删除备份（含回滚）。"""
        backup_path: Optional[str] = None
        # 临时文件使用 .xlsx 扩展名，保证 openpyxl 可按扩展名校验
        tmp_path = target_path + ".tmp.xlsx"
        try:
            if os.path.exists(target_path):
                backup_path = target_path + ".backup_" + datetime.now().strftime("%Y%m%d%H%M%S")
                shutil.copy2(target_path, backup_path)

            if self.should_cancel():
                raise OperationCancelledException("用户取消导出")

            workbook.save(tmp_path)

            if self.should_cancel():
                raise OperationCancelledException("用户取消导出")

            # 校验临时文件可被 openpyxl 正常打开
            load_workbook(tmp_path).close()

            # 替换正式文件
            if os.path.exists(target_path):
                os.remove(target_path)
            os.rename(tmp_path, target_path)

            # 删除备份
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)

        except OperationCancelledException:
            self._rollback(backup_path, tmp_path, target_path)
            raise
        except Exception as exc:  # noqa: BLE001
            self._rollback(backup_path, tmp_path, target_path)
            raise OperationFailedException(f"导出失败: {exc}") from exc

    @staticmethod
    def _rollback(backup_path: Optional[str], tmp_path: str, target_path: str) -> None:
        """回滚：恢复备份、删除临时文件。"""
        try:
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, target_path)
                os.remove(backup_path)
        except OSError:
            pass
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
