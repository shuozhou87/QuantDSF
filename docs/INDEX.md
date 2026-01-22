# QuantDSF v2 文档索引

本目录包含 QuantDSF v2 的所有技术文档。

> **最新更新**: 请查看项目根目录的 [CHANGELOG.md](../CHANGELOG.md)

---

## 📚 文档导航

### 🎯 新手入门 (Guides)

**首次使用? 从这里开始:**
1. [README.md](../README.md) - 项目概述和安装指南
2. [为什么选择 QuantDSF?](background/WHY_QUANTDSF.md) - 项目动机
3. [快速开始指南](guides/QUICK_START_SINGLE_CURVE.md)

### 🏗️ 架构与设计 (Specs)

**理解系统设计:**
- [架构设计方案 V2](specs/V2_ARCHITECTURE_PROPOSAL.md)
  - 分层架构说明、模块职责、数据流
- [输入输出规范](specs/IO_SPECIFICATION.md) **[已合并]**
  - 含完整输入格式、Export ZIP 结构、Excel 输出定义
- [用户界面规范 (UI)](specs/UI_SPECIFICATION.md) **[新]**
  - 布局结构、组件库定义、视觉风格
- [数据质量控制 (QC)](specs/QUALITY_CONTROL.md) **[重要]**
  - 评估标准、QC指标、故障排除
- [热力学QC集成](specs/QC_THERMODYNAMICS_INTEGRATION.md)
- [导出功能设计 (已归档)](archive/EXPORT_FEATURE_DESIGN.md)

### 🔬 核心功能原理 (Background & Specs)

#### Tm 分析
- [平滑算法原理](background/SMOOTHING_METHODOLOGY.md) - Savitzky-Golay 滤波器与参数选择
- [一阶导数修复记录](archive/FD_METHOD_FIX_2025.md)
- [多核并行化实现](specs/MULTICORE_PARALLELIZATION.md) - 3.96x 性能提升详解

#### 热力学分析 (核心创新)
- [单曲线热力学原理](background/SINGLE_CURVE_THERMODYNAMICS.md) - 理论基础与验证
- [热力学创新点](background/THERMODYNAMIC_INNOVATION.md)
- [典型 ΔCp 参考值](background/TYPICAL_DELTA_CP_REFERENCES.md)
- [单曲线功能集成](specs/SINGLE_CURVE_INTEGRATION.md)

#### 剂量响应 (Dose-Response)
- [静态荧光淬灭 (SFQ)](specs/SFQ_SFE.md) - 原理与实现

### 📖 用户与开发指南 (Guides)

- [单曲线分析使用教程](guides/HOW_TO_USE_SINGLE_CURVE.md)
- [导出功能用户指南](guides/EXPORT_USER_GUIDE.md)
- [TSB 平滑高级设置](guides/ADVANCED_SETTINGS_TSB_SMOOTHING.md)
- [开发者指南](guides/DEVELOPER_GUIDE.md) - 代码规范与贡献指南

### 🗄️ 归档资料 (Archive)

历史状态报告和旧会话记录已归档至 [archive/](archive/) 目录。

---

## 📝 文档贡献

### 目录结构规范
- `specs/`: 技术规格说明书 (Technical Specifications)
- `guides/`: 用户与开发指南 (Guides & Tutorials)
- `background/`: 科学原理与背景 (Scientific Background)
- `archive/`: 历史归档 (Archived Reports)

### 更新文档时
1. 对于**新功能/重要变更**: 更新根目录的 [CHANGELOG.md](../CHANGELOG.md)
2. 对于**详细技术说明**: 在 `docs/` 下相应子目录创建或更新文档
3. 更新本索引文件 (`docs/INDEX.md`)

---

## 📧 联系方式

如有问题或建议:
- 提交 [GitHub Issue](https://github.com/shuozhou87/QuantDSF/issues)
- 查看 [developer guide](guides/DEVELOPER_GUIDE.md) 获取贡献指南

---

**最后更新**: 2026-01-22
