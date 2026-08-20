"""生成演示数据 sample_data/销售数据2026.xlsx（用于试用应用）。

列结构：A=月份, B=销售额(万元), C=利润率(%), D=成本(万元)
"""
from __future__ import annotations

import math
import os
import random

from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "sample_data", "销售数据2026.xlsx")


def main() -> str:
    random.seed(42)
    wb = Workbook()
    ws = wb.active
    ws.title = "销售数据"
    ws.append(["月份", "销售额", "利润率", "成本"])
    for i in range(1, 801):
        sales = 100 + 40 * math.sin(i / 30) + random.uniform(-15, 15)
        profit = 15 + 8 * math.sin(i / 50) + random.uniform(-4, 4)
        cost = sales * (1 - profit / 100) + random.uniform(-3, 3)
        ws.append([i, round(sales, 2), round(profit, 2), round(cost, 2)])
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    print(main())
