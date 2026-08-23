"""系列映射模型（v3.2）：挂到 chart_id；行范围必填（真实 Excel 行号）。

每个系列 = 系列名 + X 列 + Y 列 + 行范围 + 颜色/形状/大小。
"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)

    series_name = Column(String(100), nullable=False)  # 用户自定义系列名
    x_col_letter = Column(String(5), nullable=False)   # X 列字母
    y_col_letter = Column(String(5), nullable=False)   # Y 列字母
    row_start = Column(Integer, nullable=False)        # 必填：该系列数据起始行（真实 Excel 行号）
    row_end = Column(Integer, nullable=False)          # 必填：该系列数据结束行

    color_hex = Column(String(7), nullable=False)      # 仅限 16 种标准色
    marker_shape = Column(String(20), nullable=False, default="circle")
    marker_size = Column(Integer, default=8)
    sort_order = Column(Integer, default=0)

    chart = relationship("Chart", back_populates="series_list")
