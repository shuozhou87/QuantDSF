# QuantDSF v2 更新日志

所有重要的项目更新都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased] - 2026-01-10

### Added
- **Complete Export Package Feature**: 一键导出所有分析结果和图表为ZIP包
  - **ZIP包内容**:
    - `QuantDSF_Results.xlsx`: 4-sheet Excel工作簿（Basic_Analysis, Dose_Response, Thermodynamics, Analysis_Settings）
    - 所有非空图表导出为300 DPI PNG（最多6张图）
  - **Excel功能**:
    - 专业格式化：蓝色标题行、冻结窗格、自动列宽
    - 数字格式化：浓度科学计数法、Tm保留1位小数、R²保留3位小数
    - QC条件格式：✅绿色、⚠️黄色、❌红色背景
    - 智能占位符：未运行的分析显示提示性说明
  - **数据存储基础设施**:
    - 新增 `dose-response-store` 和 `thermodynamics-store` 缓存分析结果
    - 修改回调函数自动保存EC50和Van't Hoff结果
  - **核心导出模块**:
    - `core/io/exporters/figure_exporter.py`: Plotly图表转PNG（kaleido引擎）
    - `core/io/exporters/excel_exporter.py`: 4-sheet工作簿生成器
    - `core/io/exporters/complete_exporter.py`: ZIP包编排器
  - **UI集成**:
    - 侧边栏"Export Results"按钮
    - 时间戳文件名（`QuantDSF_Export_YYYYMMDD_HHMMSS.zip`）
    - 浏览器自动下载
  - **实现位置**:
    - 导出器: `core/io/exporters/` (3个新文件, 673行)
    - UI: `app/layouts/main_layout.py:126`, `app/components/sidebar.py:269-276`
    - 回调: `app/callbacks/export_callbacks.py` (完全重写)
    - 存储: `app/callbacks/dose_response_callbacks.py:343-359`, `app/callbacks/thermo_callbacks.py:517-546`
  - **依赖**: kaleido 1.2.0（Plotly静态图像导出）
  - **文档**:
    - [EXPORT_FEATURE_DESIGN.md](docs/EXPORT_FEATURE_DESIGN.md) - 完整设计规范
    - [EXPORT_IMPLEMENTATION_PROGRESS.md](docs/EXPORT_IMPLEMENTATION_PROGRESS.md) - 实施进度

- **Thermodynamics QC Integration**: 完成Van't Hoff分析的质量控制集成
  - **QC状态卡片**: Van't Hoff图下方显示详细的QC评估（✅/⚠️/❌）
    - Van't Hoff回归质量（R², 数据点数, 温度范围）
    - 参数不确定性（ΔH误差, ΔS误差）
    - KD可靠性评估（298K/310K，含插值/外推状态）
    - 物理合理性检查
    - v0.9新增：温度切片数、窗口位置验证
  - **位置**: `app/callbacks/tab_callbacks.py:347`, `app/callbacks/thermo_callbacks.py:23-125, 409`
  - **文档**: [QC_THERMODYNAMICS_INTEGRATION.md](docs/QC_THERMODYNAMICS_INTEGRATION.md)

### Changed
- **放宽热力学参数合理性检查**: 避免误判有效数据
  - **ΔH检查** (`core/qc/thermo_qc.py:283-301`):
    - 旧标准: -1000 to -5 kJ/mol（严格范围）
    - 新标准: 仅标记ΔH > 50 kJ/mol的大正值为可疑
    - 原因: 小分子结合和弱相互作用的ΔH可以很小
  - **ΔS检查** (`core/qc/thermo_qc.py:303-320`):
    - 旧标准: -2500 to 0 J/mol/K
    - **新标准: 不检查**（总是通过）
    - 原因: ΔS范围高度依赖具体系统（蛋白解折叠vs配体结合vs疏水效应），无法设定通用标准
  - **降级物理合理性检查** (`core/qc/thermo_qc.py:447-449`):
    - 从critical failure（❌）降级为warning（⚠️）
    - 异常参数不再自动导致QC失败
  - **理由**: 热力学参数高度依赖实验系统，用户数据（ΔS = +28.2 cal/mol·K）对于熵驱动过程完全合理

- **调整热力学单位选择器位置**:
  - 从通用设置移至"Van't Hoff Parameters"折叠区域
  - 修复重复ID冲突（删除`tab_callbacks.py`中的duplicate）
  - 位置: `app/components/sidebar.py:119-131`

### Fixed
- **恢复浓度排序和Status tooltip功能**: 修复之前丢失的表格功能
  - **浓度排序**: 表格按浓度从低到高自动排序，无浓度样本排在最后
  - **Status tooltip**: 鼠标悬停在⚠️上显示具体原因
    - 示例: "Low R²: 0.816 (threshold: 0.90)"
    - 示例: "Low SNR: 2.1 (threshold: 3.0)" (First Derivative方法)
  - 修改位置: [app/callbacks/analysis_callbacks.py:554-656](app/callbacks/analysis_callbacks.py#L554-L656)

- **[严重] 修复TSB拟合R²显著低于V1的回归问题**: 恢复V1的初始参数策略
  - **问题**: 330nm通道RPA+ssDNA数据集TSB拟合R²平均0.84-0.94，远低于V1的0.998
  - **根本原因**: V2重写时错误使用了`_backup_v1/analysis/calc/boltzmann_fitting.py`的初始参数策略，但V1实际使用的是`_backup_v1/analysis/tm_analysis.py`中`analyze_tm_boltzmann`函数的策略
  - **关键差异**:
    1. **V1成功策略**（`analyze_tm_boltzmann`）:
       - 初猜使用数据范围的倍数关系：`A_N=F.max(), A_D=F.max()*0.8`
       - alpha/beta初猜：0.005, 0.01, 0.003（非零小值）
       - k初猜：0.3, 0.4, 0.2（较大值）
       - **无边界约束**，优化器有更大自由度
    2. **V2错误策略**（原`_fit_exponential_model`）:
       - 初猜：`A_N=0.0, A_D=0.0, alpha=0.0, beta=0.0`（退化为常数基线）
       - 严格边界：alpha/beta ∈ [-0.1, 0.1]
       - k ∈ [0.01, 1.0]
  - **修复** ([core/analysis/tm/boltzmann.py:193-235](core/analysis/tm/boltzmann.py#L193-L235)):
    1. 采用V1的3组初始参数:
       ```python
       [F.max(), 0.005, F.min(), F.max()*0.8, 0.005, F.min()*1.2, T_center, 0.3],
       [F.max(), 0.01, F.min(), F.max()*0.9, 0.01, F.min()*1.1, T_center, 0.4],
       [F.max(), 0.003, F.min(), F.max()*0.7, 0.003, F.min()*1.3, T_center, 0.2]
       ```
    2. 极大放宽边界约束（10倍原值），接近V1的无约束策略
    3. alpha/beta ∈ [-1.0, 1.0]（原[-0.1, 0.1]）
    4. k ∈ [0.001, 10.0]（原[0.01, 1.0]）
  - **修复效果**: 330nm通道RPA+ssDNA数据集
    - R²平均值: 0.8487 → **0.9977** （接近V1的0.9983）
    - R² ≥ 0.99: 6/16 (37.5%) → **15/16 (93.8%)**
    - R²最小值: 0.7038 → **0.9888**
  - **教训**: V1代码混乱有多个boltzmann实现，迁移时应识别真正使用的版本

### Added
- **改进的加载状态反馈**: 分析运行时显示更清晰的加载提示
  - 页面内容变灰并带模糊效果（opacity: 0.7, filter: blur(2px)）
  - 大号spinner（4rem × 4rem）
  - 根据分析方法动态显示具体消息:
    - Two-State Boltzmann: "🔬 Fitting Two-State Boltzmann model..."
    - AUC: "📊 Calculating Area Under Curve with Hill equation..."
    - First Derivative: "📉 Computing First Derivative peaks..."
  - 实现位置: [app/layouts/main_layout.py:41-56](app/layouts/main_layout.py#L41-L56), [app/callbacks/analysis_callbacks.py:996-1017](app/callbacks/analysis_callbacks.py#L996-L1017)
  - 用户反馈: 解决了"不知道是否卡死"的体验问题

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

- **浓度排序**: Analysis Results 表格现在按浓度从低到高自动排序
  - 没有浓度信息的样本排在最后
  - 帮助用户快速识别浓度依赖性趋势
  - 实现位置: `app/callbacks/analysis_callbacks.py:_create_results_table()`

- **质量警告详情提示**: Status 列的警告标记 (⚠️) 现在支持悬停提示
  - 鼠标悬停在 ⚠️ 上会显示具体原因
  - 例如: "Low R²: 0.444 (threshold: 0.90)"
  - 例如: "Low SNR: 2.1 (threshold: 3.0)" (一阶导数法)
  - 帮助用户快速诊断数据质量问题
  - 实现位置: `app/callbacks/analysis_callbacks.py:run_tm_analysis()`, `_create_results_table()`

### Changed
- 改进了 UI 表格的可读性，Sample 列现在显示简洁的样本标识符
- Sample 列从只读改为可编辑 (`editable: True`)
- 扩展了表格编辑 callback 以同时处理样本名称和浓度编辑
- 改进了重新分析时的数据保留逻辑,现在同时保留自定义样本名称和浓度

### Fixed
- **修复频道切换时数据保留问题**: 改进样本名称清理逻辑以正确处理 ratio 频道
  - 添加对 "350/330 nm ratio" 等复合波长标记的支持
  - 确保切换频道(330nm ↔ 350nm ↔ ratio)时用户编辑的样本名称和浓度正确保留
  - 简化匹配逻辑,依赖改进的 `clean_sample_name()` 函数
  - 实现位置: `core/utils/parser.py:clean_sample_name()`, `app/callbacks/analysis_callbacks.py`

- **[严重] 修复 Boltzmann 拟合 Tm 错误问题**: TSB 方法对某些数据给出完全错误的 Tm 值
  - **根本原因**: 指数基线模型的参数边界和初始猜测不当，导致优化器陷入局部最优解
  - **症状**: BSA 35.2 nM 样本 Tm 显示 104°C（或 37°C），而正确值应该在 ~62°C
  - **详细分析**:
    1. 原始边界允许 Tm 超出数据范围 ±10°C，k (steepness) 下界为 0.01
    2. 这导致拟合器将 Tm 推到数据范围外，用极小的 k 值强行拟合
    3. 指数基线模型对某些数据（如 BSA）过于复杂，线性模型更稳健
  - **修复方案**:
    1. 收紧 Tm 边界为 ±2°C，k 下界提高到 0.05 ([core/analysis/tm/boltzmann.py:417-431](core/analysis/tm/boltzmann.py#L417-L431))
    2. 改进初始猜测逻辑，根据信号趋势智能设置基线 ([core/analysis/tm/boltzmann.py:212-228](core/analysis/tm/boltzmann.py#L212-L228))
    3. 添加边界检查，拒绝Tm和k同时撞界的结果 ([core/analysis/tm/boltzmann.py:247-263](core/analysis/tm/boltzmann.py#L247-L263))
    4. **关键修复**: 实现指数→线性模型自动回退机制 ([app/callbacks/analysis_callbacks.py:52-82](app/callbacks/analysis_callbacks.py#L52-L82))
       - 先尝试指数模型，检查 Tm 是否在合理范围内且 k > 0.08
       - 如果不合理，自动回退到线性基线模型（更稳健）
  - **修复效果**: BSA 35.2 nM 现在正确显示 Tm ≈ 62°C（线性模型，R² = 0.9985）

- **[已回退] 修复浓度排序导致的数据错配问题**: 此问题实际上不是排序引起的
  - 原始诊断错误：怀疑是排序导致索引映射错误
  - 实际原因：Boltzmann 拟合本身就给出了错误的 Tm 值（见上一条修复）
  - 排序相关的修复（添加 `_original_index`）已实现但不是根本原因

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
