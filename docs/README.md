# QuantDSF v2 文档索引

本目录包含 QuantDSF v2 的所有技术文档。

> **最新更新**: 请查看项目根目录的 [CHANGELOG.md](../CHANGELOG.md)

---

## 📚 文档导航

### 🎯 新手入门

**首次使用? 从这里开始:**
1. [README.md](../README.md) - 项目概述和安装指南
2. [WHY_QUANTDSF.md](WHY_QUANTDSF.md) - 项目动机: 为什么需要 QuantDSF
3. [QUICK_START_SINGLE_CURVE.md](QUICK_START_SINGLE_CURVE.md) - 快速开始指南

### 🏗️ 架构与设计

**理解系统设计:**
- [V2_ARCHITECTURE_PROPOSAL.md](V2_ARCHITECTURE_PROPOSAL.md) - 完整的架构设计方案
  - 分层架构说明
  - 模块职责划分
  - 数据流设计
- [IO_SPECIFICATION.md](IO_SPECIFICATION.md) - 输入输出规范 **[重要]**
  - 支持的文件格式
  - 输出格式规范
  - 错误消息定义
  - 数据质量标准
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - 开发者指南
  - 代码规范
  - 项目结构
  - 贡献指南

### 🔬 核心功能文档

#### Tm 分析
- [SMOOTHING_METHODOLOGY.md](SMOOTHING_METHODOLOGY.md) - 信号平滑算法
  - Savitzky-Golay 滤波器
  - 参数选择策略
- [FD_METHOD_FIX_2025.md](FD_METHOD_FIX_2025.md) - 一阶导数法修复记录
- [ADVANCED_SETTINGS_TSB_SMOOTHING.md](ADVANCED_SETTINGS_TSB_SMOOTHING.md) - TSB 拟合和平滑高级设置

#### 热力学分析 (核心创新)
- [SINGLE_CURVE_THERMODYNAMICS.md](SINGLE_CURVE_THERMODYNAMICS.md) - 单曲线热力学原理
  - 理论基础
  - 算法实现
  - 验证结果
- [THERMODYNAMIC_INNOVATION.md](THERMODYNAMIC_INNOVATION.md) - 热力学模块创新点
- [HOW_TO_USE_SINGLE_CURVE.md](HOW_TO_USE_SINGLE_CURVE.md) - 单曲线分析使用教程
- [SINGLE_CURVE_INTEGRATION.md](SINGLE_CURVE_INTEGRATION.md) - 单曲线功能集成说明
- [TYPICAL_DELTA_CP_REFERENCES.md](TYPICAL_DELTA_CP_REFERENCES.md) - 典型 ΔCp 参考值

### ⚡ 性能优化

- [MULTICORE_PARALLELIZATION.md](MULTICORE_PARALLELIZATION.md) - 多核并行实现
  - 3.96x 性能提升详解
  - 实现策略
  - 性能测试结果

### 📊 项目管理

#### 状态报告
- [PROJECT_STATUS_2025_12.md](PROJECT_STATUS_2025_12.md) - 项目状态总结 (2025年12月)

#### 开发记录 (归档)
- [SESSION_UPDATE_2025-12-13.md](SESSION_UPDATE_2025-12-13.md) - 12月13日更新
- [SESSION_UPDATE_2025-12-15.md](SESSION_UPDATE_2025-12-15.md) - 12月15日更新

---

## 🗂️ 按主题浏览

### 算法相关
- 信号处理: [SMOOTHING_METHODOLOGY.md](SMOOTHING_METHODOLOGY.md)
- Tm 计算: [FD_METHOD_FIX_2025.md](FD_METHOD_FIX_2025.md), [ADVANCED_SETTINGS_TSB_SMOOTHING.md](ADVANCED_SETTINGS_TSB_SMOOTHING.md)
- 热力学分析: [SINGLE_CURVE_THERMODYNAMICS.md](SINGLE_CURVE_THERMODYNAMICS.md), [THERMODYNAMIC_INNOVATION.md](THERMODYNAMIC_INNOVATION.md)

### 性能相关
- [MULTICORE_PARALLELIZATION.md](MULTICORE_PARALLELIZATION.md)

### 科学背景
- [WHY_QUANTDSF.md](WHY_QUANTDSF.md)
- [TYPICAL_DELTA_CP_REFERENCES.md](TYPICAL_DELTA_CP_REFERENCES.md)

---

## 📝 文档贡献

### 文档命名规范
- **核心功能**: `FEATURE_NAME.md` (如 `SINGLE_CURVE_THERMODYNAMICS.md`)
- **使用指南**: `HOW_TO_*.md` 或 `*_GUIDE.md`
- **项目状态**: `PROJECT_STATUS_YYYY_MM.md`
- **会话更新**: `SESSION_UPDATE_YYYY-MM-DD.md`
- **待办事项**: `TODO_*.md`
- **Bug 修复**: `BUGFIX_*.md` 或 `*_FIX_YYYY.md`

### 更新文档时
1. 对于**新功能/重要变更**: 更新根目录的 [CHANGELOG.md](../CHANGELOG.md)
2. 对于**详细技术说明**: 在 docs/ 目录创建或更新相应文档
3. 对于**临时记录**: 使用 `SESSION_UPDATE_*.md` 格式
4. 更新本索引文件 (`docs/README.md`)

---

## 🔍 快速查找

| 我想... | 查看文档 |
|--------|---------|
| 了解项目动机 | [WHY_QUANTDSF.md](WHY_QUANTDSF.md) |
| 快速开始使用 | [QUICK_START_SINGLE_CURVE.md](QUICK_START_SINGLE_CURVE.md) |
| 理解架构设计 | [V2_ARCHITECTURE_PROPOSAL.md](V2_ARCHITECTURE_PROPOSAL.md) |
| 查看输入输出规范 | [IO_SPECIFICATION.md](IO_SPECIFICATION.md) |
| 学习单曲线热力学 | [SINGLE_CURVE_THERMODYNAMICS.md](SINGLE_CURVE_THERMODYNAMICS.md) |
| 提升分析性能 | [MULTICORE_PARALLELIZATION.md](MULTICORE_PARALLELIZATION.md) |
| 参与开发 | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| 查看更新历史 | [CHANGELOG.md](../CHANGELOG.md) |

---

## 📧 联系方式

如有问题或建议:
- 提交 [GitHub Issue](https://github.com/shuozhou87/QuantDSF/issues)
- 查看 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) 获取贡献指南

---

**最后更新**: 2026-01-09
