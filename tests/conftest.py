"""测试配置：将项目根目录与本地 libs 加入 sys.path。"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIBS = os.path.join(_ROOT, "libs")

for p in (_ROOT, _LIBS):
    if p not in sys.path:
        sys.path.insert(0, p)
