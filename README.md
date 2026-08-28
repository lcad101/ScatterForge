# Excel 散点图桌面应用

> Excel 文件"生成器/转换器"：导入原始数据 → 生成含 `raw data` + 原生散点图的全新 `.xlsx` 文件，并提供项目管理与再次编辑能力。

## 📌 项目一句话

用户导入原始 Excel → 应用读取指定行列切片 → 生成新的 `.xlsx` 文件（Sheet1 = `raw data`，Sheet2 = `Chart View` 原生散点图）→ 数据库仅记录导出文件路径与元数据（**绝不存储原始数值**）→ 后续编辑通过"写前备份 → 覆盖"闭环实现。

## 📖 文档导航

| 文档 | 说明 |
| :--- | :--- |
| [项目开发规范.md](./项目开发规范.md) | **唯一开发依据（架构冻结版 v3.2）**：6 项核心冻结决策 + 6 项 UI 决策 + 第 15 章真实需求修订（多图表/精确行列范围/系列行范围/轴步长/散点连线）。 |
| [UI预览-v3.2.html](./UI预览-v3.2.html) | **v3.2 可交互 UI 原型**（纯前端单文件）：三级树（项目组→项目→图表）、系列增删改查、轴步长/连线预览；支持 `?tab=data|series|options|preview` 演示参数。 |

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

> 试用测试样本（v3.2，仿真实报表结构）：
> - `sample_data/示例_原始报表.xlsx` —— 表头在第 17 行、数据 19~318 行分「低/中/高功率」三段，适合测试精确行列范围 + 系列行范围对比。
> - `sample_data/销售数据2026.xlsx` —— 简单表格（800 行）。
>
> 推荐试用流程：左侧点「＋项目组」/「＋项目」→ 数据设置页选 `示例_原始报表.xlsx`，起始行 17、结束行 318、起始列 A、结束列 K → 「＋新建图表」→ 系列配置页添加 3 个系列（X=F 电压、Y=H 功率，行范围 19~118 / 119~218 / 219~318）→ 图表选项设步长 → 导出。
>
> 首次运行会自动建库（`%APPDATA%\ScatterForge\scatterforge.db`，可用环境变量 `SCATTERFORGE_DB` 覆盖；检测到旧版库会自动重建）。

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

## 📝 更新记录

| 日期 | 版本 | 变更内容 |
| :--- | :--- | :--- |
| 2026-08-24 | v3.2.1 | **图表复制功能**：在图表列表支持右键菜单"📋 复制图表"及底部按钮栏"📋 复制图表"按钮，一键深复制整张图表（含全部系列配置、图表选项、限值规则），副本自动带" 副本"后缀，用户可在图表选项页自由修改名称。 |
| 2026-08-24 | v3.2.1 | **openpyxl `inf`/`nan` 兼容修复**：通过 monkey-patch 修复 openpyxl `_cast_number` 无法解析 `"inf"`/`"-inf"`/`"nan"` 字符串的缺陷，防止导入含无穷大值标记的 LED 性能测试报表时崩溃。 |
| 2026-08-24 | v3.2.1 | **当前图表高亮显示**：为项目树和图表列表面板添加 QSS 选中样式（蓝色左边框 + 浅蓝背景 + 加粗字体），用户可直观识别当前正在编辑的图表，避免误操作。 |
| 2026-08-24 | v3.2.1 | **项目复制功能**：在项目树右键项目节点弹出"📋 复制项目"菜单，一键深复制整个项目（含全部图表、系列、限值规则），副本自动带" 副本"后缀，同一项目组内新建，便于批量修改。 |
| 2026-08-24 | v3.2.1 | **预览图例右置**：图表预览中系列名称（legend）从底部移至右侧纵向排列，与导出 Excel 图表的图例位置一致，便于对照系列。 |
| 2026-08-24 | v3.2.2 | **交互优化**：① 图表列表单击即跳转预览页（不再需双击）；② 项目树取消自动展开，仅展开当前选中项；③ 树中点击图表跳转预览（与列表联动）；④ 项目组/项目右键菜单新增"✏️ 改名"。 |
| 2026-08-24 | v3.2.2 | **Bug 修复**：① 项目树展开状态在刷新后丢失（`setExpanded` 在节点加入树前调用导致不生效），改为两阶段构建；② 预览 tooltip 显示 JS 函数源码而非数据（`json.dumps` 将函数序列化为字符串），改为 HTML 模板占位符注入原始 JS；③ 图表列表选中高亮在页面跳转后消失，改用 `setCurrentRow` 确保持久。 |
| 2026-08-25 | v3.3 | **数据设置页重构（初始化流程）**：① 新增"初始化数据"流程：选择原始文件 → 选择保存路径 → 自动复制到保存路径 → 读取表格行/列数并显示 → 配置行列范围；② 所有操作基于 DB 中持久化的副本，原始文件仅初始化时使用，路径变动不影响数据；③ 数据设置页显示保存路径 + "🔄 重新初始化"按钮，支持文件迁移。 |
| 2026-08-27 | v3.3.1 | ImportView 新增 set_row_col_range()；_import() 将行列范围写入 DB；_on_project_selected() 从 DB 恢复行列范围。 |
| 2026-08-27 | v3.3.1 | Worksheet raw data does not exist 修复：_on_project_selected() 智能检测 raw data Sheet。 |
| 2026-08-27 | v3.3.1 | 项目树选中高亮修复：set_data() 新增第三阶段 setCurrentItem()。 |
| 2026-08-27 | v3.3.1 | **点击项目不再强制跳转数据设置页**：移除 `_on_project_selected()` 末尾的 `setCurrentWidget(import_view)` 调用，用户点击项目时保留当前页面不动，仅更新数据和控件状态。 |
| 2026-08-27 | v3.3.1 | **窗口最小尺寸修复**：MainWindow 新增 `setMinimumSize(1024, 600)` 覆盖子控件最小尺寸推算，消除 `QWindowsWindow::setGeometry` 警告（子控件最小宽度超过屏幕）。 |
| 2026-08-27 | v3.3.1 | **系列配置双行布局**：`SeriesRowWidget` 从单行 HBoxLayout 改为双行 QVBoxLayout（第一行：显示/名称/X列/Y列；第二行：起始行/结束行/颜色/形状/大小），小屏幕不再重叠。 |
| 2026-08-27 | v3.3.1 | **面板宽度可自由调节**：Splitter 设置 stretch factor（左0/中0/右1），左面板最小 160px、中面板最小 140px，用户可拖拽分隔条自由调整三栏宽度。 |
| 2026-08-27 | v3.3.1 | **点击项目组不再跳转项目**：`_on_group_selected()` 直接调用 `tree.set_data()` 时不传 `current_project`，避免树重建时 `setCurrentItem` 强制跳到项目，组节点正确高亮。 |
| 2026-08-27 | v3.3.1 | **项目组左键高亮修复**：`set_data()` 第三阶段新增 `sel_group` 的 `setCurrentItem()` 处理，确保左键点击项目组后组节点保持蓝色高亮（之前仅右键能高亮，因为 Qt 右键默认行为会触发 `setCurrentItem`）。 |
