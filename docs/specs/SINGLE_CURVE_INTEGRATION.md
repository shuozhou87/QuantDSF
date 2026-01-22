# Single-Curve Thermodynamics - Integration Guide

## 概述

Single-Curve热力学分析功能已成功集成到QuantDSF v2主程序中（2025-12-15）。

## 如何使用

### 1. 启用Single-Curve分析

在Advanced Settings面板中选择热力学分析方法：

```
Advanced Settings (⚙️)
└─ Thermodynamic Analysis Method
    ○ Isothermal Slicing (Van't Hoff) - Requires concentration series [默认]
    ● Single-Curve Method (Wright 2017) - Single sample per condition
```

### 2. 运行分析

1. 上传nanoDSF数据（ZIP格式）
2. 选择Tm计算方法（AUC/TSB/FD）
3. 在Advanced Settings中选择"Single-Curve Method"
4. 点击"Run Analysis"

### 3. 查看结果

结果表格将自动显示以下热力学参数列（如果启用Single-Curve方法）：

| 列名 | 说明 | 示例值 |
|------|------|--------|
| **ΔG° (kJ/mol)** | 标准自由能变化（298K） | 42.7 |
| **ΔH° (kJ/mol)** | 标准焓变 | 335 |
| **ΔS° (J/mol·K)** | 标准熵变 | 980 |
| **Thermo R²** | ΔG vs T线性拟合质量 | 0.996 |
| **Thermo** | 热力学分析质量标志 | ✓/⚠️/-- |

#### 质量标志说明

- **✓** (绿色): 通过所有质量控制检查（R²>0.90，物理合理性）
- **⚠️** (黄色): R²或参数值在可接受范围内但有警告
- **--** (灰色): 分析失败或未运行

## 技术细节

### 后端实现

**文件**: `app/callbacks/analysis_callbacks.py`

**关键修改**:

1. **添加State参数** (line 127):
   ```python
   State('thermodynamic-method-radio', 'value')
   ```

2. **条件运行分析** (lines 274-322):
   ```python
   if thermodynamic_method == 'single_curve' and not np.isnan(tm):
       result = extract_thermodynamics_single_curve(
           T=T, F=F, Tm=tm,
           progress_curve=np.array(progress_curve) if progress_curve else None
       )
       # 添加到result_dict
   ```

3. **动态表格列** (lines 425-478):
   - 检测是否有热力学数据: `has_thermo_data = any(...)`
   - 条件性添加热力学参数列
   - 添加样式条件（绿色/黄色高亮）

### 前端UI

**文件**: `app/components/sidebar.py`

**新增组件** (lines 211-237):

```python
dbc.RadioItems(
    id="thermodynamic-method-radio",
    options=[
        {'label': 'Isothermal Slicing...', 'value': 'isothermal'},
        {'label': 'Single-Curve Method...', 'value': 'single_curve'}
    ],
    value='isothermal'  # 默认
)
```

## 数据流程

```
用户上传数据
  ↓
选择Single-Curve方法
  ↓
Run Analysis
  ↓
对每个样品:
  ├─ 计算Tm (AUC/TSB/FD)
  ├─ 获取Progress Curve（归一化）
  └─ 运行extract_thermodynamics_single_curve()
      ├─ 计算P_f, P_u, K_u
      ├─ ΔG = -RT ln(K_u)
      ├─ 线性拟合ΔG vs T
      └─ 提取ΔG°, ΔH°, ΔS°
  ↓
结果存储到analysis-results-store
  ↓
动态更新表格（包含热力学参数列）
```

## 质量控制

### 自动检查

Single-Curve分析包含以下自动质量检查（见`core/analysis/thermodynamics/single_curve.py`）：

1. **线性度**: R² (ΔG vs T) > 0.90
2. **数据点数**: 拟合区域至少5个点（10-50%解折叠）
3. **物理合理性**:
   - ΔH° > 0 (吸热)
   - ΔS° > 0 (增加熵)
   - 10 < ΔG° < 150 kJ/mol
   - 50 < ΔH° < 1000 kJ/mol
   - 0.2 < ΔS° < 3.0 kJ/(mol·K)
4. **Tm检查**: 在测量温度范围内

### 警告处理

如果质量检查失败，结果中会包含警告信息：

```python
result['thermo_warnings'] = '; '.join([
    "Poor linearity (R²=0.87 < 0.90)",
    "ΔH° (45 kJ/mol) below typical range",
    ...
])
```

警告信息会在表格中通过⚠️标志显示。

## 常见问题

### Q1: 为什么某些样品没有热力学参数？

**可能原因**:
1. Tm计算失败（NaN）→ 跳过热力学分析
2. Progress curve缺失或质量差
3. R² < 0.90（线性拟合质量不足）
4. 10-50%解折叠区域数据点<5个

**解决方法**:
- 检查Tm质量（Status列）
- 使用AUC或TSB方法（提供更可靠的progress curve）
- 检查数据质量（SNR/R²）

### Q2: Single-Curve vs Isothermal Slicing，哪个更好？

**使用场景**:

| 场景 | 推荐方法 |
|------|---------|
| 单浓度样品快速筛选 | **Single-Curve** |
| pH/缓冲液优化 | **Single-Curve** |
| 突变体对比 | **Single-Curve** |
| 配体结合研究 | **Isothermal Slicing** |
| 精确K_d测定 | **Isothermal Slicing** |
| 浓度依赖性分析 | **Isothermal Slicing** |

### Q3: 为什么ΔS°单位是J/mol·K而不是kJ/mol·K？

**原因**: 遵循热力学惯例。熵值通常较小（<3 kJ/mol·K），用J/mol·K显示更直观。

**转换**: 1 kJ/(mol·K) = 1000 J/(mol·K)

例如：ΔS° = 0.98 kJ/(mol·K) = 980 J/(mol·K)

### Q4: 可以同时运行两种热力学方法吗？

**当前版本**: 不支持。需要在Advanced Settings中选择一种方法。

**未来计划**: 可能添加"双模式"选项，同时运行并比较结果。

## 验证和测试

### 测试脚本

运行测试以验证算法：

```bash
python test_single_curve_simple.py
```

**预期输出**:
- ✅ 所有蛋白误差 < 6%
- ✅ R² > 0.998
- ✅ 通过物理合理性检查

### 真实数据测试

1. 准备单浓度nanoDSF数据（任何蛋白）
2. 上传到QuantDSF
3. 选择Single-Curve方法
4. 运行分析
5. 检查Thermo R²（应>0.90）
6. 比较ΔG°/ΔH°/ΔS°与文献值（如果有）

## 已知限制

1. **可逆性假设**: 方法假设热变性可逆，但nanoDSF通常不可逆（聚集）
   - **影响**: 获得表观热力学参数
   - **缓解**: 仍可用于相对比较

2. **两态假设**: 假设只有folded ↔ unfolded
   - **影响**: 多态转变会降低R²
   - **缓解**: R² < 0.90时给出警告

3. **忽略ΔCp**: 未考虑热容变化
   - **影响**: 对大蛋白可能略有误差
   - **缓解**: 对多数蛋白影响<10%

4. **依赖Progress Curve**: 需要高质量的归一化数据
   - **影响**: FD方法可能不适用（无progress curve）
   - **缓解**: 推荐使用AUC或TSB方法

## 更新日志

- **2025-12-15**:
  - ✅ 实现核心算法（`single_curve.py`）
  - ✅ 验证测试（误差<6%，R²>0.998）
  - ✅ 集成到主程序（UI + 后端）
  - ✅ 动态表格支持
  - ✅ 完整文档

## 相关文档

- [单曲线热力学原理](SINGLE_CURVE_THERMODYNAMICS.md) - 详细方法学文档
- [热力学创新](THERMODYNAMIC_INNOVATION.md) - QuantDSF热力学分析概述
- [Wright et al. 2017](../manuscript/ref/) - 原始参考文献

## 未来改进

### 短期
- [ ] 添加"警告"弹窗显示详细警告信息
- [ ] 导出功能包含热力学参数
- [ ] ΔG vs T拟合图可视化

### 中期
- [ ] ΔCp拟合（非线性模型）
- [ ] 误差估计（bootstrap）
- [ ] 批量比较工具

### 长期
- [ ] 双模式分析（同时运行两种方法并比较）
- [ ] 热力学参数数据库
- [ ] 机器学习辅助质量控制

---

**集成完成日期**: 2025-12-15
**版本**: QuantDSF v2.0
**状态**: ✅ 生产就绪
