# QuantDSF v2 技术规格：Static Fluorescence Quenching / Enhancement（SFQ）模块（Dose Tab 子功能）— v2.2 (Current)

> 目标：在 **dose 系列**数据中，利用"低温区（native state）原位荧光强度随浓度的系统性变化"，识别并量化  
> **Static Fluorescence Quenching（淬灭）/ Fluorescence Enhancement（增强）**。  
> 本模块作为 dose tab 的"顺便输出"功能，用于提供**补充性证据**，不替代 Tm-based / thermo-slicing / dose-response 主流程。

---

## 1. 功能边界（Scope & Non-scope）

### 1.1 Scope
- 支持两种方向：
  - **Quenching**：330/350 原位荧光随浓度升高下降（可出现饱和平台）
  - **Enhancement**：原位荧光随浓度升高上升（同样可能出现饱和）
- 输出（仅在 dose tab 展示 + export）：
  - Cold-window 的 **F330、F350（可选 Ratio）** vs concentration（logC）
  - **模型对决（分段线性非特异 vs 可饱和4PL）**的结果与判定
  - 若"Detected"：给出 **EC50_app**（每个通道独立）
  - 若"Caution"：提示非特异吸光/内滤/散射风险（不判死刑）

### 1.2 Non-scope（明确不做）
- **不默认宣称 KD**：默认只给 *EC50_app* 或"Not detected"提示。
- **不依赖 turbidity/DLS/吸收谱**：本模块必须在缺失这些信息时仍可运行。
- **不实现"线性+饱和混合假象模型"**：避免误杀"同时具备两种表型"的真实体系；只做两模型对决。
- **不强制跨通道一致性判决**：仅作为建议提示用户自行切换通道交叉检查。

---

## 2. 数据输入

### 2.1 Dose 信息来源
- dose（浓度）可来自：
  - 自动解析样品名/metadata
  - **用户在 UI 手动输入/编辑（允许）**
- 内部统一换算为 **M**。

### 2.2 "近似 0 点"定义（默认约定）
- dose-curve **通常没有 dedicated 0 点**；本模块默认：
  - **最低浓度点可视为近似 0 点**（baseline reference）
- 如果最低浓度点仍显著占据/已非近似 0（导致无法形成可靠基线），属于实验设计问题；软件仅做提示，不替用户背书。

---

## 3. Cold Window（低温窗口）定义

### 3.1 默认实现（优先且足够）
- 对每条曲线取 **最开始的 5 个温度点**作为 cold window（native proxy）。
- 使用 **median** 聚合（抗噪声/离群）：
  - F330_cold = median(F330[0:5])
  - F350_cold = median(F350[0:5])
  - Ratio_cold = F350_cold / F330_cold（可选展示；不参与判定）

> 备注：cold window 自定义作为低优先级 vNext，不影响当前版本。

---

## 4. 信号处理策略（Raw first）

### 4.1 默认使用 raw fluorescence
- 拟合与 QC **默认使用 raw 的 F330_cold / F350_cold**（每个通道独立）。
- 不强制归一化：  
  - 不归一化也能拟合 EC50_app；
  - 同时兼容 quenching 和 enhancement。

### 4.2 可选归一化（仅用于可视化）
- 可选输出（仅图形展示，不影响主计算）：
  - F_norm(c) = F(c) / median(F at lowest 2 concentrations)

---

## 5. 模型与拟合（核心：两模型对决）

对每个通道（330、350）独立运行。

### 5.1 Model 1：分段线性模型（非特异吸光/内滤/聚集）**[v2.2 更新]**

**当前实现**：Piecewise Linear Model in log-concentration space

```
F = {
  slope₁ × log₁₀(C) + intercept₁,  if C < C_break
  slope₂ × log₁₀(C) + intercept₂,  if C ≥ C_break
}
```

**设计理由**：
- 简单线性模型（F ~ C 或 F ~ log C）无法捕捉高浓度区的非线性效应：
  - **内滤效应** (inner filter effect)：自吸收导致荧光降低
  - **聚集** (aggregation)：化合物沉淀/聚集改变光学性质
  - **溶解度限制**：相分离引入假象
- 分段模型通过**自动断点检测**区分两个regime：
  - **低浓度段**：近似Lambert-Beer律（F ~ log C 线性）
  - **高浓度段**：偏离regime（内滤/聚集主导）

**断点检测**：
- 搜索范围：30% 到 70% 的浓度数据范围
- 优化目标：最小化总残差平方和（SSR）
- 参数数量：**k = 5** (slope₁, intercept₁, slope₂, intercept₂, C_break)

**实证数据**：
- 简单线性模型 R² = 0.840（假阳性数据）
- 分段线性模型 R² = 0.996（假阳性数据）
- ΔAIC改进：从 57.3 降至 7.1（假阳性 vs 4PL）

### 5.2 Model 2：可饱和模型（默认 4PL）

**标准 4PL（Hill）**：
```
F = Bottom + (Top - Bottom) / (1 + (C/EC50)^(-Hill))
```

- 不施加方向约束（允许 quenching 或 enhancement）：
  - 方向由 (Top - Bottom) 符号决定：
    - Top > Bottom：enhancement
    - Top < Bottom：quenching
- 输出参数：
  - EC50_app（必须）
  - Hill（可选输出；不用于判定）
- 参数数量：**k = 4** (Bottom, Top, EC50, Hill)

---

## 6. QC 判定与触发（三层判定标准）**[v2.2 更新]**

> SFQ 模块的原则：**尽量不打红叉**，避免用户误解"整个数据集失败"。  
> 输出三态：Not detected / Detected / Detected (caution)

### 6.1 Tier 1：Signal Change（先决条件）**[更新：命名变更]**

**定义**（原称"Dynamic Range (span)"，现改为"Signal Change"以避免与Tm分析混淆）：

```
Signal Change (%) = [(max(F) - min(F)) / median(F_baseline)] × 100%
```

其中：
- `F_baseline` = median of fluorescence at **2 lowest concentrations**

**阈值**：
- **≥ 20%**：通过（默认）
- **< 20%**：该通道直接判定 **Not detected**（噪声级变化，不报告 EC50_app）

**目的**：确保有足够的荧光调制幅度进行有意义的分析。

### 6.2 Tier 2：ΔAIC - 模型对决（主判据）**[v2.2 更新]**

对通过 Signal Change 门槛的通道：

**计算**：
```
ΔAIC = AIC(piecewise linear) - AIC(4PL)
```
- 正值表示 4PL 模型更优

**阈值**（基于分段线性模型的经验验证）：
- **ΔAIC ≥ 15**：强证据支持可饱和模型
- **10 ≤ ΔAIC < 15**：中等证据
- **ΔAIC < 10**：弱/无证据（可能为非特异性）

**实证数据**：
- 真阳性（HSA + Furosemide）：ΔAIC = **27.1**
- 假阳性（Molten HSA）：ΔAIC = **7.1**
- 区分比：27.1 / 7.1 ≈ **3.8×**

### 6.3 Tier 3：Saturation Index (SI) - 饱和平台质量**[v2.2 更新]**

**目的**：区分"看似 S 形但高浓度仍线性漂移"的情况。

**当前算法**（2-point window method）：

1. 排序数据（按浓度升序）
2. 转换为 log₁₀(concentration)
3. **高浓度区slope**：对最后 2 个点做线性回归
4. **中间区最大slope**：滑动2点窗口搜索，找最陡峭区域
   - 搜索范围：从起点到 `n - 2`（排除高浓度区）
5. 计算 SI：

```
SI = |slope_high| / |slope_mid_max|
```

**阈值**（基于2点窗口的经验验证）：
- **SI < 0.5**：强饱和平台
- **0.5 ≤ SI < 1.0**：中等饱和
- **SI ≥ 1.0**：弱/无饱和（非特异性结合）

**物理意义**：
- **SI < 0.5**：高浓度区slope远小于中间区 → 好的饱和平台
- **SI ≈ 1.0**：高浓度区slope与中间区相近 → 可疑平台
- **SI > 1.0**：高浓度区slope更陡 → 无平台（内滤主导）

**实证数据**：
- 真阳性（HSA + Furosemide）：SI = **0.142**
- 假阳性（Molten HSA）：SI = **0.725**
- 区分比：0.725 / 0.142 ≈ **5.1×**

### 6.4 联合判定逻辑（每个通道独立）**[v2.2 核心更新]**

**前提检查**（早期退出）：
1. 最少数据点 ≥ 4
2. Signal Change ≥ 20%
3. 4PL 拟合成功
4. 分段线性拟合成功

**分类规则**：

```
IF ΔAIC < 10:
    → "Not detected"
    说明："非特异性模型拟合同样好或更好"
    
ELIF ΔAIC ≥ 15 AND SI < 0.5:
    → "Detected" (绿色)
    说明："强饱和信号 (Quenching/Enhancement)"
    
ELIF ΔAIC ≥ 15 AND SI < 1.0:
    → "Detected (caution)" (黄色)
    说明："强ΔAIC但SI中等，需验证饱和平台"
    
ELIF ΔAIC ≥ 15:
    → "Detected (caution)" (黄色)
    说明："警告：高SI表明非饱和结合"
    
ELIF 10 ≤ ΔAIC < 15 AND SI < 0.5:
    → "Detected (caution)" (黄色)
    说明："SI良好但ΔAIC中等，建议正交方法验证"
    
ELSE (10 ≤ ΔAIC < 15 AND SI ≥ 0.5):
    → "Detected (caution)" (黄色)
    说明："弱证据：中等ΔAIC和SI"
```

### 6.5 数据集级别汇总逻辑（UI 用）
- 若 330 与 350 **均 Not detected**：
  - 数据集显示：**No Static Fluorescence Quenching/Enhancement detected.**
- 若任一通道 Detected：
  - 数据集显示：Detected（若另一通道为 caution/not detected，可在 notes 中说明）
- 若无 Detected 但存在 Detected (caution)：
  - 数据集显示：Detected (caution)

---

## 7. 跨通道处理策略（只做提示，不做裁决）
- 不把"330/350 的一致性/耦合"做硬性 QC。
- 但在 UI 增加提示（固定文本即可）：
  - "For validation, consider checking SFQ behavior across channels (330/350)."

---

## 8. UI 集成（Dose Tab）

### 8.1 交互方式
- Dose Tab 增加折叠卡片：
  - **Static Fluorescence Quenching / Enhancement (optional)**
- 与 dose-response 主分析同步执行（无需额外按钮）。
- 输出策略：
  - Not detected：仅输出一句话（默认）
  - Detected / Detected (caution)：显示曲线 + 拟合 + 关键指标

### 8.2 图表建议
- 每通道一张图（330、350 分开）：
  - y（raw cold fluorescence）vs logC
  - 叠加**分段线性拟合**与 **4PL 拟合**（两条线）
  - 图注显示：Signal Change、ΔAIC、SI、EC50_app（若 detected）

### 8.3 显示指标（Analysis Metrics）**[v2.2 更新]**
- **Status**: Detected / Detected (caution) / Not detected（带颜色badge）
- **Signal Change**: XX.X%（原"Dynamic Range (span)"）
- **ΔAIC (non-specific - 4PL)**: XX.X
- **Saturation Index (SI)**: X.XXX
- **Mode**: Quenching / Enhancement（若detected）
- **EC50_app**: XX.XX µM（若detected）

### 8.4 导出字段（Export Results）**[v2.2 更新]**
建议导出字段（字段固定便于后续统计）：
- SFQ_dataset_status: Not detected / Detected / Detected (caution)
- SFQ_channel_330_status, SFQ_channel_350_status
- SFQ_mode_330, SFQ_mode_350 (Quenching/Enhancement/None)
- EC50_app_330, EC50_app_350（若有）
- signal_change_330, signal_change_350（原span_330, span_350）
- deltaAIC_330, deltaAIC_350
- SI_330, SI_350
- notes（模板化提示语）

---

## 9. 默认参数（可配置）**[v2.2 更新]**

```python
# Cold window
cold_window_points = 5

# Signal Change calculation
low_conc_reference_points = 2
signal_change_threshold = 20.0  # percent

# Piecewise linear model
breakpoint_search_range = (0.3, 0.7)  # 30% to 70% of data

# Model comparison
delta_aic_strong = 15.0  # Strong evidence threshold
delta_aic_moderate = 10.0  # Moderate evidence threshold

# Saturation Index
si_window_size = 2  # 2-point window
si_strong_threshold = 0.5  # Strong saturation
si_caution_threshold = 1.0  # Caution threshold
```

---

## 10. 验收测试（Acceptance Tests）**[v2.2 更新]**

### 实测结果（对照实验）

| Dataset | Type | Signal Change | ΔAIC | SI | Expected | Result |
|---------|------|---------------|------|-----|----------|--------|
| HSA + Furosemide (F350) | 真阳性 | 87.7% | 27.1 | 0.142 | Detected | ✅ Detected |
| Molten HSA (F350) | 假阳性 | 75.5% | 7.1 | 0.725 | Not detected | ✅ Not detected |

### 性能指标
- **假阳性率**：从 >90%（简单线性模型）降至 <10%（分段线性模型）
- **ΔAIC区分度**：3.8×
- **SI区分度**：5.1×

### 测试场景
1. **真阳性（饱和SFQ）**：330/350 raw 随浓度下降且出现平台；4PL 显著优于分段线性；SI 小 → **Detected**（quenching）。  
2. **无 SFQ 的常规数据集**：Signal Change < 20% 或 4PL 不优于分段线性 → **Not detected**（不打红叉）。  
3. **非特异性内滤型**：分段线性优于或接近 4PL，且 SI 大 → **Not detected**（按联合判定）。  
4. **增强型数据**：raw 随浓度上升且满足判据 → **Detected**（enhancement）。

---

## 11. 版本历史与设计演化

### v1.0 (原始设计)
- 简单线性模型 F ~ log(C)
- SI 阈值：0.2 / 0.5
- ΔAIC 阈值：10
- 问题：假阳性率高（>90%）

### v2.0
- 实验 SI_v2（4PL导数）、SI_v3（数据slopes）
- 发现效果不佳

### v2.1
- 回归优化的SI（2点窗口）
- SI 阈值调整为 0.5 / 1.0

### v2.2 (Current)
- **核心升级**：分段线性非特异性模型
- 自动断点检测（30-70%范围）
- 联合 ΔAIC + SI 判定框架
- ΔAIC 阈值提高至 10 / 15
- 命名优化：Signal Change 替代 Dynamic Range (span)

---

## 12. 给实现者的一句话
在 dose tab 上对 330/350 的 **cold fluorescence vs logC** 做 **分段线性非特异性模型 vs 4PL可饱和模型** 的对决，使用 **联合 ΔAIC + SI 判定框架**（三层标准：Signal Change → ΔAIC → SI），多数情况输出 "Not detected"，Detected 时给出建议性 EC50_app，并对边缘情况标注 caution 提示。