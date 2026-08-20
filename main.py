"""ScatterForge —— Excel 散点图生成器 程序入口。"""
import os
import sys


def _bootstrap_libs() -> None:
    """允许使用本地 vendor 目录（libs/）运行，避免依赖系统环境变量。"""
    libs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
    if os.path.isdir(libs) and libs not in sys.path:
        sys.path.insert(0, libs)


def main() -> int:
    _bootstrap_libs()

    from src.core.database import init_db
    from src.ui.main_window import run_app

    init_db()
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
