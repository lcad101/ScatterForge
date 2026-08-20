"""主题分组模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)  # 新增(2026-08-20 Q5)：拖拽排序
    created_at = Column(DateTime, default=datetime.now)

    projects = relationship(
        "Project", back_populates="theme", cascade="all, delete-orphan"
    )
