"""校验规则测试（冻结规范附录 B）。"""
from src.models.validators import (
    EXCEL_SAFE_COLORS,
    col_to_index,
    index_to_col,
    validate_col_letter,
    validate_color_hex,
    validate_marker_shape,
)


def test_col_letter_roundtrip():
    assert col_to_index("A") == 1
    assert col_to_index("Z") == 26
    assert col_to_index("AA") == 27
    assert col_to_index("XFD") == 16384
    assert index_to_col(1) == "A"
    assert index_to_col(27) == "AA"
    assert index_to_col(16384) == "XFD"


def test_validate_col_letter():
    assert validate_col_letter("A")
    assert validate_col_letter("zzz")  # 自动大写，语法合法（3 位字母）
    assert validate_col_letter("XFE")  # 语法合法（3 位字母）
    assert not validate_col_letter("")   # 空
    assert not validate_col_letter("A1")   # 含数字
    assert not validate_col_letter("ABCD")  # 超过 3 位


def test_validate_col_in_range():
    from src.models.validators import validate_col_in_range
    assert validate_col_in_range("XFD")     # Excel 最大列
    assert not validate_col_in_range("XFE")  # 超出最大列


def test_validate_color_hex():
    assert validate_color_hex("#FF0000")
    assert validate_color_hex("#00b050")  # 忽略大小写（绿色）
    assert not validate_color_hex("#00ff00")  # 纯绿非 16 标准色之一
    assert not validate_color_hex("FF0000")   # 缺 #


def test_validate_marker_shape():
    assert validate_marker_shape("circle")
    assert validate_marker_shape("TRIANGLE")
    assert not validate_marker_shape("star")
    assert not validate_marker_shape("")


def test_palette_size():
    assert len(EXCEL_SAFE_COLORS) == 16
    assert len(set(EXCEL_SAFE_COLORS)) == 16
