"""图表项目主表（v3.2）：一个项目 = 一个原始数据表格。

仅存储导出文件路径 + 精确行列范围（真实 Excel 行列号）+ 状态元数据，
绝不存储任何原始数值。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base

ACTIVE = "ACTIVE"
MISSING = "MISSING"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    group_id = Column(Integer, ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False)

    # 【唯一存储的"数据"】导出文件的绝对路径（原始文件路径绝不入库）
    source_file_path = Column(String(500), nullable=False)

    # 数据范围（真实 Excel 行列号，含表头所在行；无表头假设）
    data_start_row = Column(Integer, nullable=False, default=1)
    data_end_row = Column(Integer, nullable=True)   # NULL = 仅取起始行
    data_start_col_letter = Column(String(5), nullable=False, default="A")
    data_end_col_letter = Column(String(5), nullable=True)  # NULL = 仅取起始列

    # 状态与时间戳
    status = Column(String(20), default=ACTIVE)  # ACTIVE | MISSING
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_opened_at = Column(DateTime, nullable=True)

    # 关系
    group = relationship("ProjectGroup", back_populates="projects")
    charts = relationship(
        "Chart", back_populates="project", cascade="all, delete-orphan",
        order_by="Chart.sort_order",
    )
