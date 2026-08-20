"""系列映射模型。"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    series_name = Column(String(100), nullable=False)  # 用户自定义系列名称
    x_col_letter = Column(String(5), nullable=False)  # X 轴列字母，如 "A"
    y_col_letter = Column(String(5), nullable=False)  # Y 轴列字母，如 "C"
    color_hex = Column(String(7), nullable=False)  # 仅限 16 种标准色，如 "#FF0000"
    marker_shape = Column(String(20), nullable=False, default="circle")
    marker_size = Column(Integer, default=8)
    sort_order = Column(Integer, default=0)

    project = relationship("Project", back_populates="series_list")
