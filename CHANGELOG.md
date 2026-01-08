# QuantDSF v2 更新日志

所有重要的项目更新都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased] - 2026-01-08

### Added
- **样本名称自动清理功能**: 在 Analysis Results 表格中的 Sample 列现在会自动清理冗余信息
  - 自动移除浓度信息（科学计数法、带单位、小数格式）
  - 移除占位浓度 `_0_`
  - 移除波长标记 (`_330 nm`, `_350 nm`, `_ratio`)
  - 移除文件类型标记 (`_unfolding`, `_raw`, `_processed` 等)
  - 示例: `XBB_1.25E-5_0_330 nm_unfolding_raw` → `XBB`
  - 实现位置: `core/utils/parser.py:clean_sample_name()`
  - 影响文件: `core/io/parsers/prometheus.py`, `core/io/parsers/tycho.py`

- **可编辑的样本名称**: Sample 列现在可以直接编辑
  - 用户可以自定义样本名称 (例如: `XBB` → `Mpro+Nirmatrelvir`)
  - 编辑的名称会在切换标签页时保留
  - 编辑的名称会在重新分析时保留（使用相同数据集时）
  - 只有在上传新文件或明确删除文件时才会重置
  - 实现位置: `app/callbacks/analysis_callbacks.py:update_table_edits()`
  - 状态管理: 原始名称保存在 `result['original_name']` 中

### Changed
- 改进了 UI 表格的可读性，Sample 列现在显示简洁的样本标识符
- Sample 列从只读改为可编辑 (`editable: True`)
- 扩展了表格编辑 callback 以同时处理样本名称和浓度编辑
- 改进了重新分析时的数据保留逻辑,现在同时保留自定义样本名称和浓度

---

## [2.0.0-alpha] - 2025-12-11

### Initial Release - 完全重写

#### Added - 核心功能
- **分层架构设计**
  - UI 层 (Dash) 完全解耦于核心计算层
  - 模块化组件设计
  - 集中式状态管理

- **Tm 分析方法** (熔点确定)
  - Two-State Boltzmann 拟合
  - 一阶导数法
  - AUC (曲线下面积) 方法

- **热力学分析模块**
  - Van't Hoff 线性回归
  - EC₅₀/Kd 确定
  - 单曲线热力学参数提取 (创新功能)
  - 等温剂量响应分析

- **质量控制指标**
  - 信噪比 (SNR) 计算
  - R² 拟合优度
  - 动态范围评估

- **性能优化**
  - 多核并行处理: 3.96x 性能提升 (245 样本: 162s → 41s)
  - 自适应 CPU 核心检测
  - 利用率: 80-95% CPU

- **用户界面**
  - Dash Bootstrap 响应式界面
  - PyWebView 桌面应用包装
  - 交互式 Plotly 图表
  - 实时数据可视化

- **数据输入输出**
  - Prometheus NT.48 数据解析器
  - Tycho NT.6 数据解析器 (CSV 和 Excel)
  - Excel 格式结果导出
  - 浓度信息自动提取

- **数据持久化**
  - SQLAlchemy ORM 模型
  - Repository 模式数据访问

#### Changed
- 从 Streamlit 迁移到 Dash 框架
- 完全重构代码架构
- 使用 Pydantic 进行数据验证

#### Deprecated
- Streamlit v1 版本已停用

#### Technical Details
- Python 3.12+
- 30+ 技术文档
- 类型安全: 100% 类型提示覆盖
- 测试框架: pytest

---

## 文档结构说明

### 核心文档 (必读)
- `V2_ARCHITECTURE_PROPOSAL.md` - 架构设计方案
- `WHY_QUANTDSF.md` - 项目动机和价值
- `DEVELOPER_GUIDE.md` - 开发者指南

### 功能文档
- `MULTICORE_PARALLELIZATION.md` - 多核并行实现
- `SINGLE_CURVE_THERMODYNAMICS.md` - 单曲线热力学分析
- `SMOOTHING_METHODOLOGY.md` - 平滑算法文档
- `THERMODYNAMIC_INNOVATION.md` - 热力学创新说明

### 部署文档
- `DESKTOP_APP_GUIDE.md` - 桌面应用使用指南
- `NUITKA_BUILD_GUIDE.md` - Nuitka 编译指南
- `DESKTOP_PACKAGING_STATUS.md` - 打包状态

### 使用指南
- `HOW_TO_USE_SINGLE_CURVE.md` - 单曲线分析使用教程
- `QUICK_START_SINGLE_CURVE.md` - 快速开始指南

### 性能分析
- `PERFORMANCE_ANALYSIS_200_SAMPLES.md` - 大数据集性能测试

### 历史记录 (归档)
- `SESSION_UPDATE_2025-12-*.md` - 会话更新记录
- `UPDATES-121225.md` - 历史更新
- `CONSOLIDATED_UPDATES.md` - 合并更新

### 待办事项 (可能过时)
- `TODO_*.md` - 各类待办事项
- `BUGFIX_TODO.md` - Bug 修复列表

### 参考资料
- `TYPICAL_DELTA_CP_REFERENCES.md` - ΔCp 参考值
- `ADVANCED_SETTINGS_TSB_SMOOTHING.md` - 高级设置说明

---

## 版本编号说明

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范:
- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

---

## 链接

- [GitHub 仓库](https://github.com/shuozhou87/QuantDSF)
- [问题追踪](https://github.com/shuozhou87/QuantDSF/issues)
