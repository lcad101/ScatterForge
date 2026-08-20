# Excel 散点图桌面应用

> Excel 文件"生成器/转换器"：导入原始数据 → 生成含 `raw data` + 原生散点图的全新 `.xlsx` 文件，并提供项目管理与再次编辑能力。

## 📌 项目一句话

用户导入原始 Excel → 应用读取指定行列切片 → 生成新的 `.xlsx` 文件（Sheet1 = `raw data`，Sheet2 = `Chart View` 原生散点图）→ 数据库仅记录导出文件路径与元数据（**绝不存储原始数值**）→ 后续编辑通过"写前备份 → 覆盖"闭环实现。

## 📖 文档导航

| 文档 | 说明 |
| :--- | :--- |
| [项目开发规范.md](./项目开发规范.md) | **唯一开发依据（架构冻结版 v3.1）**：6 项核心冻结决策 + 6 项 UI 决策（第 14 章）、数据流、数据库 Schema、UI 规范、导出覆盖策略、性能验收标准、开发计划调整、16 色表与校验规则。 |
| [UI预览.html](./UI预览.html) | 可交互 UI 原型（纯前端单文件），用于预览界面效果；支持 `?tab=preview`、`?view=export`、`?view=missing` 演示参数。 |

## 🧭 核心冻结决策速览（6 项）

1. **行选取**：用户指定起始行/结束行（QSpinBox），缺省结束行仅取一行；预览 >5000 行时前端静默降采样前 5000 点，导出仍全量写入。
2. **导出结构**：内存新建 `Workbook()` → `raw data` 页写切片数据 → `Chart View` 页生成 `openpyxl.chart.ScatterChart` 原生散点图 → 保存为 `原文件名_Scatter_{时间戳}.xlsx`；**禁止修改原用户文件**。
3. **列选取**：用户输入起始列/结束列（QLineEdit，字母 A~ZZZ）；`ExcelHandler` 以 `read_only` 模式**只解析 min_col~max_col 区间**，禁止全量扫描。
4. **持久化**：SQLite **严禁存储任何原始数值**，仅存导出文件绝对路径 + 行列范围 + 元数据；体积 ≤ 100MB；文件缺失 → MISSING 灰色状态 → 可"删除"（仅删 DB）或"重新定位"。
5. **进度与取消**：耗时类必须实现 `IStoppable`（`_kill_flag`），每 1000 行检查一次；取消后执行回滚三要素（删临时文件、回滚事务、还原原文件）。
6. **样式降级（方案 A 静默降级）**：调色板仅 16 种标准色（见规范附录 A），形状仅 `circle/diamond/square/triangle`，直接透传给 openpyxl。

## 🎨 新增 UI 决策速览（6 项，2026-08-20 确认）

| 决策 | 结论 |
| :--- | :--- |
| Q1 深色模式 | 暂不支持（仅浅色主题） |
| Q2 项目列表多选 | 支持 Ctrl/Shift 多选 + 批量导出/删除（MISSING 不可选） |
| Q3 预览缩放/平移 | 支持（ECharts dataZoom + toolbox） |
| Q4 导出图片 | 支持 PNG / SVG（ExportImageDialog） |
| Q5 主题拖拽排序 | 支持（themes 加 `sort_order`，仅排序不可跨主题移动） |
| Q6 最近项目 | 启动页显示最近 5 个项目（projects 加 `last_opened_at`） |

> 新增字段：`themes.sort_order`、`projects.last_opened_at`；开发计划增量 **+4.0 天**（见规范第 9.5、14 章）。

## 🛠 技术栈

Python 3.10+ · PySide6/PyQt6 · openpyxl · ECharts（QWebEngineView 嵌入预览）· SQLite + SQLAlchemy · pandas

## 🚀 快速开始

```bash
# 1. 安装依赖（建议在虚拟环境内）
python -m pip install -r requirements.txt

# 2. 运行应用
python main.py

# 3. 运行测试
python -m pytest tests -q
```

> 试用演示数据：`sample_data/销售数据2026.xlsx`（800 行：月份 / 销售额 / 利润率 / 成本）。首次运行会自动建库（`%APPDATA%\ScatterForge\scatterforge.db`，可用环境变量 `SCATTERFORGE_DB` 覆盖）。

## 📁 项目结构

```
main.py                      # 程序入口
requirements.txt             # 依赖清单
src/
├── core/                    # database / exceptions / stoppable
├── models/                  # Theme / Project / Series / validators
├── services/                # excel_handler / chart_builder / excel_export_service / file_probe_service
└── ui/
    ├── main_window.py       # 主窗口编排
    ├── widgets/             # 主题树 / 项目列表 / ECharts 预览
    ├── views/               # 数据设置 / 系列配置 / 图表选项
    ├── dialogs/             # 导出 / 导出图片
    └── assets/echarts.min.js
scripts/make_sample_data.py  # 生成演示数据
tests/                       # pytest 单元测试
sample_data/                 # 演示数据
```

## 📋 开发阶段提醒（来自冻结规范）

- **Week 1**：实现冻结版 Schema（themes / projects / series + 索引）；新增 `themes.sort_order`、`projects.last_opened_at`、最近项目查询（+0.5 天）。
- **Week 2**：`ExcelHandler` 列区间流式读取，验证"仅读 2 列 ≤ 5 秒"。
- **Week 3**：`ChartBuilder` + `ExcelExportService` 全新文件生成；+ ECharts dataZoom/toolbox（+0.5 天）。
- **Week 4**：UI 主窗口；+ 主题树拖拽排序（+0.5 天）。
- **Week 5**：配置面板 + 预览；+ 项目列表多选 + 批量操作工具栏（+1.0 天）。
- **Week 6**：导出唯一模式 + 写前备份 + 灰色项目删除按钮；+ 导出为图片 PNG/SVG（+1.0 天）。

> ⚠️ 本文件为架构冻结文档（v3.1）的索引；任何需求变更须走《架构变更请求（ACR）》并经客户签字（见规范第 10 章）；新增 UI 决策以第 14 章为准。
