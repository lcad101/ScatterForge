"""项目组模型（原 themes 更名，2026-08-20 v3.2）。

树层级：项目组 → 项目（数据表）→ 图表 → 系列。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base


class ProjectGroup(Base):
    __tablename__ = "project_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)  # 拖拽排序
    created_at = Column(DateTime, default=datetime.now)

    projects = relationship(
        "Project", back_populates="group", cascade="all, delete-orphan",
        order_by="Project.id",
    )
