"""代码强制校验规则（冻结规范第 12 章附录 B）。"""
from __future__ import annotations

import re
from enum import Enum


class MarkerShape(str, Enum):
    CIRCLE = "circle"
    DIAMOND = "diamond"
    SQUARE = "square"
    TRIANGLE = "triangle"


EXCEL_SAFE_COLORS: list[str] = [
    "#FF0000", "#C00000", "#FFC000", "#FFD966",
    "#FFFF00", "#92D050", "#00B050", "#006100",
    "#00B0F0", "#0070C0", "#0000FF", "#7030A0",
    "#FF00FF", "#FF99CC", "#A52A2A", "#000000",
]

# 颜色中文名（用于 UI 调色板提示）
EXCEL_SAFE_COLOR_NAMES: list[str] = [
    "红色", "深红", "橙色", "金色", "黄色", "亮绿", "绿色", "深绿",
    "青色", "深蓝", "蓝色", "紫色", "洋红", "粉色", "棕色", "黑色",
]

_COL_RE = re.compile(r"^[A-Z]{1,3}$")


def validate_color_hex(color: str) -> bool:
    """校验颜色是否为 16 种标准色之一。"""
    return color.upper() in {c.upper() for c in EXCEL_SAFE_COLORS}


def validate_marker_shape(shape: str) -> bool:
    """校验点形状是否为 4 种之一。"""
    return shape.lower() in {item.value for item in MarkerShape}


def validate_col_letter(col: str) -> bool:
    """校验列字母语法是否合法（1~3 位纯字母，A~ZZZ），见冻结规范附录 B。"""
    return bool(col) and bool(_COL_RE.match(col.upper()))


def validate_col_in_range(col: str) -> bool:
    """校验列是否在 Excel 有效范围内（≤ XFD）。超出时由 UI 弹窗提示。"""
    return col_to_index(col) <= col_to_index("XFD")


def col_to_index(col: str) -> int:
    """列字母转 1 基索引：A→1, Z→26, AA→27。"""
    col = col.upper()
    num = 0
    for ch in col:
        num = num * 26 + (ord(ch) - ord("A") + 1)
    return num


def index_to_col(idx: int) -> str:
    """1 基索引转列字母：1→A, 27→AA。"""
    s = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        s = chr(ord("A") + rem) + s
    return s
