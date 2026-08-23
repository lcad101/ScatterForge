"""数据库连接与会话管理（SQLite + SQLAlchemy 2.0）。

冻结规范第 5 章：SQLite 严禁存储任何原始数值，仅存导出文件路径 + 元数据。
数据库体积契约：即使管理 1 万个项目，SQLite ≤ 100MB。
"""
from __future__ import annotations

import os
import sqlite3
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


def _is_old_schema(path: Path) -> bool:
    """检测旧版/混合损坏库：v3.1 themes 表、projects 缺 group_id、series 缺 chart_id。"""
    try:
        conn = sqlite3.connect(str(path))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "themes" in tables:
            conn.close()
            return True
        if "projects" in tables:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)")}
            if "group_id" not in cols or "data_start_row" not in cols:
                conn.close()
                return True
        if "series" in tables:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(series)")}
            if "chart_id" not in cols or "row_start" not in cols:
                conn.close()
                return True
        if "chart_limits" in tables:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(chart_limits)")}
            if "x_start" not in cols or "y_min" not in cols:
                conn.close()
                return True
        conn.close()
    except Exception:  # noqa: BLE001
        pass
    return False


def _rebuild_db() -> None:
    """删除旧库文件；失败则降级为逐表 DROP；再失败则改名旧库文件让位。"""
    try:
        _DB_PATH.unlink()
        return
    except OSError:
        pass
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        rows = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for name in rows:
            conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        conn.commit()
        conn.close()
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        _DB_PATH.rename(_DB_PATH.with_name(_DB_PATH.name + ".bak"))
    except OSError:
        pass


def init_db() -> None:
    """创建全部表（幂等）。

    v3.2 迁移：检测到旧版（v3.1 themes 表）或损坏库（projects 缺 group_id）时，
    删除数据库重建。数据库仅存导出文件路径 + 元数据（无原始数值），重建无数据损失。
    """
    from src import models  # noqa: F401  注册模型

    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    if _DB_PATH.exists() and _is_old_schema(_DB_PATH):
        _rebuild_db()

    Base.metadata.create_all(engine)


def db_path() -> Path:
    return _DB_PATH
