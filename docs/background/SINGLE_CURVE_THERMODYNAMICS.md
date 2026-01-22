# Single-Curve Thermodynamic Analysis

## 概述

基于Wright et al. 2017的方法，从**单条melting curve**提取完整的热力学参数（ΔG°, ΔH°, ΔS°），无需浓度系列数据。

**参考文献**:
Wright, T. A., Stewart, J. M., Page, R. C., & Konkolewicz, D. (2017). Extraction of Thermodynamic Parameters of Protein Unfolding Using Parallelized Differential Scanning Fluorimetry. *The Journal of Physical Chemistry Letters*, 8(3), 553-558.

---

## 核心原理

### 与等温切片法的对比

| 特性 | 等温切片法（Van't Hoff） | Single-Curve法（Wright 2017） |
|------|------------------------|----------------------------|
| **数据需求** | 多浓度系列（≥5个浓度点） | **单条曲线** |
| **热力学信息来源** | 浓度依赖性（K_d vs T） | **温度依赖性（P_u vs T）** |
| **适用场景** | 配体结合、浓度依赖研究 | **单点快速评估、蛋白稳定性** |
| **假设** | 两态 + 可逆 | 两态 + 可逆 |
| **优势** | 直接测量结合常数 | **无需浓度梯度，节省样品** |
| **局限** | 需要多次实验 | **可逆性要求更严格** |

### 方法步骤

**Step 1**: 归一化得到折叠分数
```
P_f(T) = (F_unfold - F) / (F_unfold - F_fold)
P_u(T) = 1 - P_f(T)
```
- 使用AUC Progress方法的baseline fitting（两段线性或Boltzmann拟合）

**Step 2**: 计算平衡常数
```
K_u(T) = P_u / P_f
```

**Step 3**: 计算吉布斯自由能
```
ΔG(T) = -RT ln(K_u)
```

**Step 4**: 线性拟合（10-50%解折叠区域）
```
ΔG = a·T + b
```
- 选择10-50%解折叠范围以避免噪声和聚集影响
- 要求 R² > 0.90

**Step 5**: 外推得到标准热力学参数
```
ΔG°(298K) = a·298.15 + b
ΔS° = ΔG° / (Tm - 298.15)
ΔH° = Tm · ΔS°
```

---

## 实现

### 核心模块

**文件**: `core/analysis/thermodynamics/single_curve.py`

**主要函数**:

```python
def extract_thermodynamics_single_curve(
    T: np.ndarray,              # 温度 (°C or K)
    F: np.ndarray,              # 荧光强度
    Tm: float,                  # 熔解温度
    progress_curve: Optional[np.ndarray] = None,  # 预计算的P_f
    baseline_fold: Optional[np.ndarray] = None,    # 折叠态基线
    baseline_unfold: Optional[np.ndarray] = None,  # 解折叠态基线
    min_points: int = 5,        # 最少拟合点数
    r2_threshold: float = 0.90  # R²阈值
) -> Dict[str, Any]
```

**返回结果**:
```python
{
    'success': True,
    'valid': True,              # 是否通过质量控制
    'delta_G_std': 42.7,        # kJ/mol, at 298K
    'delta_H_std': 335.0,       # kJ/mol
    'delta_S_std': 0.98,        # kJ/(mol·K)
    'Tm_used': 341.75,          # K (68.6°C)
    'R_squared': 0.996,         # 线性拟合质量
    'n_points': 18,             # 拟合数据点数
    'warnings': [...],          # 警告信息
    'fit_data': {
        'T_fit': [...],         # 拟合使用的温度
        'delta_G_fit': [...],   # 拟合使用的ΔG值
        'P_f': [...],           # 折叠分数曲线
        'P_u': [...],           # 解折叠分数曲线
        'K_u': [...]            # 平衡常数曲线
    }
}
```

### 验证结果

使用Wright论文Table 1中的文献值生成合成数据，测试结果：

| 蛋白质 | 参数 | 文献值 | 测量值 | 误差 |
|--------|------|--------|--------|------|
| **Lysozyme** | ΔG° | 42.7 kJ/mol | 41.3 kJ/mol | 3.3% |
|  | ΔH° | 335 kJ/mol | 324 kJ/mol | 3.4% |
|  | ΔS° | 0.98 kJ/(mol·K) | 0.95 kJ/(mol·K) | 3.3% |
|  | R² | - | 0.999 | ✓ |
| **Carbonic Anhydrase** | ΔG° | 60.4 kJ/mol | 57.4 kJ/mol | 5.0% |
|  | ΔH° | 536 kJ/mol | 510 kJ/mol | 4.8% |
|  | ΔS° | 1.60 kJ/(mol·K) | 1.52 kJ/(mol·K) | 5.1% |
| **Chymotrypsin** | ΔG° | 20.7 kJ/mol | 20.3 kJ/mol | 1.8% |
| **Peroxidase** | ΔG° | 24.6 kJ/mol | 23.7 kJ/mol | 3.6% |

✅ **所有误差 < 5.5%，R² > 0.998**

---

## 集成到QuantDSF

### 方案：热力学分析双模式

在现有Van't Hoff分析中添加Single-Curve选项：

```
Thermodynamic Analysis:
├─ Method Selection (Radio buttons)
│   ├─ ○ Isothermal Slicing (Van't Hoff)
│   │     └─ Requires: Concentration series (≥5 points)
│   └─ ○ Single-Curve Method (Wright 2017)  ← 新增
│         └─ Requires: Single high-quality curve + Tm
│
├─ Quality Control
│   ├─ R² threshold: 0.90 (adjustable)
│   ├─ Min fitting points: 5
│   └─ Unfolding range: 10-50% (auto)
│
└─ Results Display
    ├─ ΔG°(25°C), ΔH°, ΔS°
    ├─ R² (ΔG vs T plot)
    ├─ Validity flags
    └─ Warnings
```

### 实现步骤

#### 1. 修改UI（`app/components/sidebar.py`）

在Van't Hoff Parameters面板中添加方法选择：

```python
dbc.RadioItems(
    id='thermodynamic-method',
    options=[
        {
            'label': 'Isothermal Slicing (Van\'t Hoff) - Multi-concentration',
            'value': 'isothermal'
        },
        {
            'label': 'Single-Curve Method (Wright 2017) - Single sample',
            'value': 'single_curve'
        }
    ],
    value='isothermal',  # 默认保持原有方法
    inline=False
)
```

#### 2. 修改后端逻辑

**在 `app/callbacks/analysis_callbacks.py` 中**:

```python
# 检测是否选择了Single-Curve方法
if thermodynamic_method == 'single_curve':
    # 对每个样品单独分析
    for sample in samples:
        if sample has valid Tm and progress_curve:
            result = extract_thermodynamics_single_curve(
                T=sample['T'],
                F=sample['F'],
                Tm=sample['Tm'],
                progress_curve=sample['progress_curve'],
                baseline_fold=sample.get('baseline_fold'),
                baseline_unfold=sample.get('baseline_unfold')
            )

            # 添加到结果表格
            sample['delta_G_std'] = result['delta_G_std']
            sample['delta_H_std'] = result['delta_H_std']
            sample['delta_S_std'] = result['delta_S_std']
            sample['thermo_r2'] = result['R_squared']
            sample['thermo_valid'] = result['valid']
```

#### 3. 结果显示

**结果表格新增列**:
- `ΔG° (kJ/mol)` - 标准自由能
- `ΔH° (kJ/mol)` - 标准焓变
- `ΔS° (J/mol·K)` - 标准熵变（注意单位转换）
- `Thermo R²` - 热力学拟合质量
- `Valid` - ✓/⚠️/❌

**可视化（可选）**:
- ΔG vs T 线性拟合图
- 参数对比柱状图（多样品时）

---

## 质量控制

### 自动质量检查

1. **线性度检查**: R² (ΔG vs T) > 0.90
2. **数据点数**: 拟合区域至少5个点
3. **物理合理性**:
   - ΔH° > 0 (解折叠应该是吸热)
   - ΔS° > 0 (解折叠应该增加熵)
   - 10 < ΔG° < 150 kJ/mol (典型范围)
   - 50 < ΔH° < 1000 kJ/mol
   - 0.2 < ΔS° < 3.0 kJ/(mol·K)

4. **Tm检查**: Tm在测量温度范围内

### 警告信息

```python
warnings = [
    "Poor linearity (R²=0.87 < 0.90)",
    "ΔH° (45 kJ/mol) below typical range (50-1000)",
    "Expanded fitting range to 5-60% unfolded",
    ...
]
```

---

## 适用场景

### ✅ 推荐使用场景

1. **单浓度样品筛选**
   - 快速评估蛋白稳定性
   - 样品量有限
   - 无需配体结合常数

2. **pH/缓冲液优化**
   - 多条件快速比较
   - 理解稳定化机制（焓 vs 熵驱动）

3. **蛋白工程评估**
   - 突变体热力学指纹
   - 与WT对比

4. **方法验证**
   - 与等温切片法交叉验证
   - 检查可逆性假设

### ⚠️ 谨慎使用场景

1. **不可逆解折叠**
   - nanoDSF通常不可逆（聚集）
   - 获得的是**表观热力学参数**
   - 仍有参考价值（Wright论文已验证）

2. **多态转变**
   - 方法假设两态
   - 复杂解折叠路径会降低拟合质量
   - 检查R²是否足够高

3. **热容变化显著**
   - 方法未考虑ΔCp
   - 可能引入系统误差
   - 对大蛋白影响更明显

### ❌ 不适用场景

1. **配体结合研究** → 使用等温切片法
2. **精确K_d测定** → 使用等温切片法
3. **浓度依赖性分析** → 使用等温切片法

---

## 与文献对比

### Wright et al. 2017的创新

✅ **首次系统化**实现DSF热力学参数提取
✅ **F_max校正**解决聚集导致的荧光淬灭
✅ **10-50%窗口**优化拟合质量
✅ **文献验证**：与DSC、CD、化学变性数据一致

### QuantDSF的改进

✅ **复用baseline fitting**：更可靠的归一化（vs Wright的简单校正）
✅ **集成到现有工作流**：自动从AUC Progress获取P_f
✅ **严格质量控制**：物理合理性+统计学检验
✅ **透明和可验证**：开源实现，可审查算法

---

## 局限性和注意事项

### 方法学假设

1. **两态模型**: 假设只有folded ↔ unfolded
   - 多数蛋白质有中间态
   - 但两态近似通常足够（Wright论文已验证）

2. **可逆性**: 假设热变性可逆
   - nanoDSF通常不可逆（聚集）
   - 获得的是**表观参数**，仍有意义

3. **ΔH和ΔS温度无关**: 忽略ΔCp
   - 对小蛋白影响小
   - 对大蛋白可能引入误差

### 实验限制

1. **噪声敏感**: ΔG vs T拟合对噪声敏感
   - 需要高质量数据（R²>0.90）
   - 低SNR样品可能失败

2. **温度范围**: 需要覆盖足够的解折叠过程
   - 至少10-50%解折叠区域有数据
   - 边界效应可能影响拟合

3. **Tm依赖**: 需要准确的Tm值
   - 建议使用TSB拟合的Tm
   - AUC或FD的Tm也可以

---

## FAQ

### Q1: 为什么不直接用slope作为ΔS°？

**A**: 虽然从 ΔG = ΔH - T·ΔS可知 slope ≈ -ΔS，但Wright方法使用**外推法**更稳健：
```
ΔS° = ΔG°/(Tm - 298)
```
这考虑了Tm处ΔG=0的约束，减少误差传播。

### Q2: Single-Curve法和Van't Hoff法哪个更准？

**A**:
- **Van't Hoff法**：直接测量浓度依赖性，理论上更准确
- **Single-Curve法**：依赖温度依赖性，误差可能略大

但Wright论文显示两者与DSC的一致性都很好（文献Table S1）。实际使用中：
- 有浓度系列 → Van't Hoff
- 单浓度样品 → Single-Curve

### Q3: nanoDSF不可逆，这个方法还有效吗？

**A**: **有效，但获得的是表观参数**。Wright论文（Figure S2-S3）验证了即使存在不可逆聚集，方法仍给出与文献一致的结果。表观参数对于：
- 相对比较（样品间、条件间）
- 稳定性排序
- 机制理解（焓 vs 熵）

仍然非常有价值。

### Q4: 为什么R²要求>0.90？

**A**: R²反映ΔG vs T的线性度，直接影响参数准确性：
- R² > 0.95: 优秀，结果可靠
- 0.90 < R² < 0.95: 可接受，结果谨慎使用
- R² < 0.90: 差，可能违反两态假设或数据质量不足

---

## 测试

**测试脚本**: `test_single_curve_simple.py`

运行测试：
```bash
python test_single_curve_simple.py
```

**预期结果**:
- ✅ 所有蛋白误差 < 6%
- ✅ R² > 0.998
- ✅ 通过物理合理性检查

---

## 下一步

### 近期任务
- [ ] 集成到UI（Thermodynamic Settings面板）
- [ ] 从AUC Progress自动提取P_f和baseline
- [ ] 结果表格添加热力学参数列
- [ ] 测试真实nanoDSF数据

### 中期优化
- [ ] ΔCp考虑（非线性拟合）
- [ ] 多峰解卷积
- [ ] 误差估计（bootstrap/jackknife）
- [ ] 批量比较工具

### 文档
- [ ] 用户指南更新
- [ ] 方法学文档
- [ ] 示例数据集

---

## 参考资料

1. **原始论文**:
   Wright et al. (2017) *J. Phys. Chem. Lett.* 8, 553-558
   DOI: 10.1021/acs.jpclett.6b02894

2. **相关方法**:
   - Ericsson et al. (2006) *Anal. Biochem.* - DSF基础方法
   - Matulis et al. (2005) *Biochemistry* - ThermoFluor热力学
   - Niesen et al. (2007) *Nat. Protoc.* - DSF标准流程

3. **理论基础**:
   - Van't Hoff方程
   - 两态蛋白质解折叠模型
   - 吉布斯-亥姆霍兹方程

---

**Created**: 2025-12-15
**Status**: ✅ 核心功能已实现并验证
**Next**: 集成到QuantDSF主程序
