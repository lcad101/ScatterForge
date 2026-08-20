"""图表项目主表模型（核心资产）。

冻结规范第 5 章：本表【唯一存储的数据】是导出文件的绝对路径 source_file_path，
绝不存储任何原始数值（浮点数/字符串）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base

ACTIVE = "ACTIVE"
MISSING = "MISSING"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    theme_id = Column(Integer, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False)

    # 【唯一存储的"数据"】导出文件的绝对路径
    source_file_path = Column(String(500), nullable=False)

    # 行列切片元数据（用于从 raw data 页重新读取）
    raw_start_row = Column(Integer, nullable=False, default=1)
    raw_end_row = Column(Integer, nullable=True)  # NULL = 仅取一行
    raw_start_col_letter = Column(String(5), nullable=False)  # 如 "A"
    raw_end_col_letter = Column(String(5), nullable=True)  # NULL = 仅取一列

    # 图表元数据
    chart_title = Column(String(200), nullable=True)
    x_axis_label = Column(String(100), nullable=True)
    y_axis_label = Column(String(100), nullable=True)
    x_axis_min = Column(Float, nullable=True)
    x_axis_max = Column(Float, nullable=True)
    y_axis_min = Column(Float, nullable=True)
    y_axis_max = Column(Float, nullable=True)
    show_grid = Column(Boolean, default=True)

    # 状态与时间戳
    status = Column(String(20), default=ACTIVE)  # ACTIVE | MISSING
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_opened_at = Column(DateTime, nullable=True)  # 新增(2026-08-20 Q6)

    # 关系
    theme = relationship("Theme", back_populates="projects")
    series_list = relationship(
        "Series",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Series.sort_order",
    )
