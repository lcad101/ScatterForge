"""数据库连接与会话管理（SQLite + SQLAlchemy 2.0）。

冻结规范第 5 章：SQLite 严禁存储任何原始数值，仅存导出文件路径 + 元数据。
数据库体积契约：即使管理 1 万个项目，SQLite ≤ 100MB。
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 可通过环境变量覆盖数据库路径；默认位于用户目录下（跨文件位置稳定）。
_DEFAULT_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "ScatterForge"
_DB_PATH = Path(os.environ.get("SCATTERFORGE_DB", _DEFAULT_DIR / "scatterforge.db"))


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""


def _make_engine(url: str):
    return create_engine(
        url,
        connect_args={"check_same_thread": False},
        future=True,
    )


engine = _make_engine(f"sqlite:///{_DB_PATH}")
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """创建全部表（幂等）。"""
    # 导入模型以确保注册到 Base.metadata
    from src import models  # noqa: F401

    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def db_path() -> Path:
    return _DB_PATH
