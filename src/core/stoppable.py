"""可停止（可取消）任务接口。

架构强制约束（冻结规范第 7.3 节）：
所有耗时类（ExcelHandler / ChartBuilder / ExcelExportService）必须实现本接口，
在循环体内每处理 1000 行（或每写入一个 Sheet）调用一次 :meth:`should_cancel`。
"""
from __future__ import annotations


class IStoppable:
    """耗时任务统一取消接口。"""

    def __init__(self) -> None:
        self._kill_flag = False

    def cancel(self) -> None:
        """请求取消：设置终止标志。"""
        self._kill_flag = True

    def should_cancel(self) -> bool:
        """检查是否收到取消请求。"""
        return self._kill_flag
