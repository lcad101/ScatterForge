"""图表模型（v3.2 新增）：一个项目多张图。

图表名 chart_name 同时用作导出文件的 Sheet 名。
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base


class Chart(Base):
    __tablename__ = "charts"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    chart_name = Column(String(200), nullable=False)   # 图表名（= 输出 Sheet 名）
    chart_title = Column(String(200), nullable=True)
    x_axis_label = Column(String(100), nullable=True)
    y_axis_label = Column(String(100), nullable=True)

    x_axis_min = Column(Float, nullable=True)
    x_axis_max = Column(Float, nullable=True)
    y_axis_min = Column(Float, nullable=True)
    y_axis_max = Column(Float, nullable=True)

    # 刻度（模仿 Excel 大网格 + 小网格；NULL = 自动）
    x_axis_major_unit = Column(Float, nullable=True)   # X 步长（主要刻度单位）
    x_axis_minor_unit = Column(Float, nullable=True)   # X 最小网格步长（次要刻度单位）
    y_axis_major_unit = Column(Float, nullable=True)
    y_axis_minor_unit = Column(Float, nullable=True)

    show_grid = Column(Boolean, default=True)
    connect_line = Column(Boolean, default=True)       # 散点连线（折线连接）

    sort_order = Column(Integer, default=0)

    project = relationship("Project", back_populates="charts")
    series_list = relationship(
        "Series", back_populates="chart", cascade="all, delete-orphan",
        order_by="Series.sort_order",
    )
    limits = relationship(
        "ChartLimit", back_populates="chart", cascade="all, delete-orphan",
        order_by="ChartLimit.sort_order",
    )
