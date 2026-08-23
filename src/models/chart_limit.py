"""条件限值规则模型（v3.2）：X 列区间 → Y 列最小/最大限值，检测超限。"""
from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base


class ChartLimit(Base):
    __tablename__ = "chart_limits"

    id = Column(Integer, primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    x_col_letter = Column(String(5), nullable=False)   # X 列（如电压列）
    y_col_letter = Column(String(5), nullable=False)   # Y 列（如功率列）
    x_start = Column(Float, nullable=False)            # X 范围下限
    x_end = Column(Float, nullable=False)              # X 范围上限
    y_min = Column(Float, nullable=False)              # Y 下限
    y_max = Column(Float, nullable=False)              # Y 上限
    sort_order = Column(Integer, default=0)

    chart = relationship("Chart", back_populates="limits")
