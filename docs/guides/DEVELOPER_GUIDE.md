# QuantDSF v2 开发者指南

本指南聚焦 v2 代码（当前活跃代码在 `core/` 与 `app/`；旧版已归档到 `_backup_v1/`）。发布前内部使用。

## 1. 环境与启动
- Python 3.9+，建议使用 conda 或 venv。
- 依赖安装：`pip install -r requirements_v2.txt`
- 启动：`python app_v2.py --debug --port 8052`
- 入口：`app_v2.py` 创建 Dash 应用，核心逻辑在 `core/`，UI 在 `app/`。

## 2. 目录结构（v2）
- `core/`：纯算法与数据模型
  - `analysis/tm/`：Tm 方法（Boltzmann、AUC、Derivative）
  - `analysis/thermodynamic/`：Van’t Hoff、Isothermal、EC50→KD
  - `io/parsers/`：Prometheus、Tycho 解析（过滤 turbidity）
  - `io/exporters/`：CSV/Excel
  - `models/`：Pydantic 数据模型
  - `pipeline.py`：分析管道编排
- `app/`：Dash UI
  - `layouts/`：页面布局（basic/thermo/dose）
  - `components/`：上传/表格/图表/侧边栏
  - `callbacks/`：file / analysis / thermo / tab 管理
  - `state.py`：共享状态
- `scripts/`：调试脚本（如 `debug_progress_rpa.py`）
- `tests/`：Pytest（示例在 `tests/core/`）
- `_backup_v1/`：已归档的 v1 代码与文档（含原始 `analysis/ processing/ ui/ utils/` 等）。

## 3. 运行流程（关键回调与数据流）
1) 上传解析：`app/callbacks/file_callbacks.py` → `core.io.parsers.parse_zip_file` → 生成 capillary 列表（含 T/F/浓度）。
2) 基础分析：`analysis_callbacks.py` 调用 `calc_tm_auc`（默认 progress/AUC）或其他方法，结果存入 `analysis-results-store`。
3) Thermo 页：
   - `thermo_callbacks.populate_vh_table` / `populate_isothermal_table` 从 `analysis-results-store` 填表。
   - Van’t Hoff：`run_vanthoff_analysis` 读取表格选中的点，支持蛋白浓度→KD 转换，自适应单位，输出 ΔH/ΔS/KD/R²。
   - Isothermal：`build_isothermal_table` 生成温度切片的 EC50/KD/DR/R²。
   - AUC Overlay：`update_overlay_plot`，优先用进度曲线；质量差则回退原始 min-max。

## 4. 近期关键实现与修复
- AUC progress 基线：改为首尾 15% 线性基线归一化，指数拟合失败时不影响可视化；必要时尝试指数/线性 Boltzmann，再失败才导数回退。
- 浓度解析：`core/utils/parser.parse_concentration` 优先科学计数法，避免误取前置浓度。
- Turbidity 过滤：`core/io/parsers/__init__.py` 跳过含 “turbidity” 文件。
- Tab 切换不丢数据：`tab_callbacks.render_basic_tab` 使用 `no_update` 保留渲染结果；上传/删除会清空 store。
- Van’t Hoff：自适应 KD 单位、25°C 与 37°C KD 输出、温度区间选择、数据选择表（R²≥0.9 自动选）、AUC overlay 修复。
- Isothermal 表：DR = max-min(norm F)，EC50→KD 逐行转换，分页 25。
- KD 统一 Morrison 转换，无 cutoff。
- 热力学单位切换（Joule/Calorie）与 NumPy 2.0 兼容性修正。

## 5. 开发/调试提示
- 端口占用：改用 `--port 8052`。
- 日志：`app.log`（启动命令中重定向）。
- 快速诊断 AUC/TSB：`python scripts/debug_progress_rpa.py`（RPA+SSDNA 数据集示例，检查翻转、fallback、R²）。
- 新增模块请保持类型注解，核心逻辑避免依赖 Dash。
- 若需对比 v1，参见 `_backup_v1/` 内对应目录（已完整归档）。

## 6. 待办/关注（简述）
- 继续收敛 Thermo 页的回归表现与用户体验（颜色梯度、图例精简已做）。
- 若需公开发布，再补充用户向 README 与打包指引。

