"""业务异常体系。

所有业务异常统一继承自 :class:`OperationFailedException`；
用户主动取消统一抛出 :class:`OperationCancelledException`。
"""


class OperationFailedException(Exception):
    """业务操作失败的基类异常。"""


class OperationCancelledException(OperationFailedException):
    """用户主动取消操作（如导出/导入），触发回滚流程。"""


class FileMissingException(OperationFailedException):
    """目标文件不存在或已失效。"""


class ValidationError(OperationFailedException):
    """输入校验未通过（列字母 / 颜色 / 形状等）。"""
