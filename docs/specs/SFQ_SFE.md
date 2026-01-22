# QuantDSF v2 技术规格：Static Fluorescence Quenching / Enhancement（SFQ）模块（Dose Tab 子功能）— v1.0 (Final)

> 目标：在 **dose 系列**数据中，利用“低温区（native state）原位荧光强度随浓度的系统性变化”，识别并量化  
> **Static Fluorescence Quenching（淬灭）/ Fluorescence Enhancement（增强）**。  
> 本模块作为 dose tab 的“顺便输出”功能，用于提供**补充性证据**，不替代 Tm-based / thermo-slicing / dose-response 主流程。

---

## 1. 功能边界（Scope & Non-scope）

### 1.1 Scope
- 支持两种方向：
  - **Quenching**：330/350 原位荧光随浓度升高下降（可出现饱和平台）
  - **Enhancement**：原位荧光随浓度升高上升（同样可能出现饱和）
- 输出（仅在 dose tab 展示 + export）：
  - Cold-window 的 **F330、F350（可选 Ratio）** vs concentration（logC）
  - **模型对决（线性 vs 可饱和）**的结果与判定
  - 若“Detected”：给出 **EC50_app**（每个通道独立）
  - 若“Caution”：提示非特异吸光/内滤/散射风险（不判死刑）

### 1.2 Non-scope（明确不做）
- **不默认宣称 KD**：默认只给 *EC50_app* 或“Not detected”提示。
- **不依赖 turbidity/DLS/吸收谱**：本模块必须在缺失这些信息时仍可运行。
- **不实现“线性+饱和混合假象模型”**：避免误杀“同时具备两种表型”的真实体系；只做两模型对决。
- **不强制跨通道一致性判决**：仅作为建议提示用户自行切换通道交叉检查。

---

## 2. 数据输入

### 2.1 Dose 信息来源
- dose（浓度）可来自：
  - 自动解析样品名/metadata
  - **用户在 UI 手动输入/编辑（允许）**
- 内部统一换算为 **M**。

### 2.2 “近似 0 点”定义（默认约定）
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

> 备注：cold window 自定义作为低优先级 vNext，不影响 v1.0。

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

### 5.1 Model 1：线性模型（非特异吸光/内滤/散射常见形态）
- 推荐在 logC 空间：
  - y = a * logC + b
- （实现细节：logC 用 log10(M)，注意处理浓度单位与 0/缺失）

### 5.2 Model 2：可饱和模型（默认 4PL）
- **默认标准 4PL（Hill）**：
  - y = Bottom + (Top - Bottom) / (1 + (x/EC50)^Hill)
- 不施加方向约束（允许 quenching 或 enhancement）：
  - 方向由 (Top - Bottom) 符号决定：
    - Top > Bottom：enhancement
    - Top < Bottom：quenching
- 输出参数：
  - EC50_app（必须）
  - Hill（可选输出；不用于判定）

---

## 6. QC 判定与触发（只做建议性背书）

> SFQ 模块的原则：**尽量不打红叉**，避免用户误解“整个数据集失败”。  
> 输出三态：Not detected / Detected / Detected (caution)

### 6.1 入口门槛：动态范围（硬标准）
对每个通道单独计算：

- y = {F_cold at each dose point}
- y_low = y 在低浓度区（默认最低 2 个浓度点）
- span = (max(y) - min(y)) / median(y_low)

**要求：span ≥ 30%**
- 若 <30%：该通道直接判定 **Not detected**（不报告 EC50_app）

### 6.2 模型对决：AIC/BIC +（可选）交叉验证
对通过 span 门槛的通道：

- 计算 AIC 与/或 BIC：
  - AIC_linear, AIC_4PL
  - BIC_linear, BIC_4PL（可选）
- 判定建议（默认用 AIC，BIC 可作为辅助）：
  - 若 **AIC_4PL 显著优于 AIC_linear**（例如 ΔAIC ≥ 10）→ 倾向可饱和
  - 若 **AIC_4PL 仅略优或不优**（ΔAIC < 10 或 AIC_4PL ≥ AIC_linear）→ 不背书饱和

**交叉验证（推荐实现，作为稳健性加分项）**
- 例如对 dose 点做 K-fold（K=3 或 5）或留一法：
  - 计算 CV error：CV_linear vs CV_4PL
- 若 4PL 在 CV 上同样明显更好 → 加强“Detected”可信度  
- 若 CV 不支持（4PL 过拟合） → 转入 caution 或 not detected（见 6.4）

> 实现建议：AIC 作为主判据，CV 作为“tie-breaker/加分项”，避免计算量过大。

### 6.3 饱和指数（Saturation Index, SI）：高浓度区是否真的"平"
目的：区分"看似 S 形但高浓度仍线性漂移"的情况。

- 取 high-C window（默认最高 3 个点，或 min(3, floor(N/3))）
  - 在 logC 空间拟合线性：y = a_high * logC + b
- 取 mid window：**使用滑动窗口找最陡峭区域**（改进算法）
  - 从低浓度到中浓度滑动，找 |slope| 最大的窗口
  - 这比固定选取中间区域更准确地捕捉转折点
  - 拟合线性：y = a_mid * logC + b
- 定义：
  - **SI = |a_high| / (|a_mid| + eps)** （eps 防止除 0）

**实际采用阈值**（v1.0 实现）：
- SI < 0.3：高浓度区接近平台（支持饱和）→ **Detected**
- SI 0.3–0.6：边缘（caution）→ **Detected (caution)**
- SI > 0.6：不太像平台（更像线性/非特异趋势）

> 注：原设计文档建议 SI < 0.2 / 0.2-0.5 / >0.5，但实测发现对于高质量数据过严，
> 实际实现放宽为 0.3 / 0.6 以减少误报。

> SI 作为 QC 辅助，不单独否定；与模型对决结合使用。

### 6.4 最终状态判定（每个通道独立）
对每个通道给出 status，再汇总到数据集级别。

**Not detected**
- span < 30%，或
- 4PL 未显著优于线性（ΔAIC < 10 且 CV 不支持），或
- 4PL 拟合失败/不收敛

**Detected**
- span ≥ 30%
- ΔAIC ≥ 10（4PL 显著优于线性）
- 且 SI < 0.2（或 SI 在可接受范围内，且 CV 支持）

**Detected (caution)**
- span ≥ 30%
- 4PL 优于线性但不够“压倒性”（例如 2 ≤ ΔAIC < 10），或
- ΔAIC 很好但 SI 较大（例如 SI ≥ 0.2），提示高浓度区仍有线性漂移风险，或
- AIC 支持但 CV 不支持（疑似过拟合）

### 6.5 数据集级别汇总逻辑（UI 用）
- 若 330 与 350 **均 Not detected**：
  - 数据集显示：**No Static Fluorescence Quenching/Enhancement detected.**
- 若任一通道 Detected：
  - 数据集显示：Detected（若另一通道为 caution/not detected，可在 notes 中说明）
- 若无 Detected 但存在 Detected (caution)：
  - 数据集显示：Detected (caution)

---

## 7. 跨通道处理策略（只做提示，不做裁决）
- 不把“330/350 的一致性/耦合”做硬性 QC。
- 但在 UI 增加提示（固定文本即可）：
  - “For validation, consider checking SFQ behavior across channels (330/350/ratio).”

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
  - 叠加线性拟合与 4PL 拟合（两条线）
  - 图注显示：span、ΔAIC、SI、EC50_app（若 detected）

### 8.3 导出字段（Export Results）
建议新增 SFQ section（字段固定便于后续统计）：
- SFQ_dataset_status: Not detected / Detected / Detected (caution)
- SFQ_channel_330_status, SFQ_channel_350_status
- SFQ_mode_330, SFQ_mode_350 (Quenching/Enhancement/None)
- EC50_app_330, EC50_app_350（若有）
- span_330, span_350
- deltaAIC_330, deltaAIC_350（AIC_linear - AIC_4PL）
- SI_330, SI_350
- notes（模板化提示语）

---

## 9. 默认参数（可配置）
- Cold window points: 5
- Low-conc reference: lowest 2 points
- Span threshold: 30%
- High-C window points: 3（v1.0 实现）
- Mid window: 滑动窗口找最陡峭区域（v1.0 改进）
- Model comparison:
  - ΔAIC threshold for strong support: 10
  - Weak support (caution): 2–10
- SI thresholds（v1.0 实现值）:
  - strong plateau: **<0.3**（原设计 0.2）
  - caution: **0.3–0.6**（原设计 0.2–0.5）
  - likely non-plateau: **>0.6**（原设计 0.5）

> v1.0 实现说明：SI 阈值从原设计放宽，因实测发现原阈值对高质量数据过严。

---

## 10. 验收测试（Acceptance Tests）
1) **CA2 + furosemide**：330/350 raw 随浓度下降且出现平台；4PL 显著优于线性；SI 小 → Detected（quenching）。  
2) **无 SFQ 的常规数据集**：span <30% 或 4PL 不优于线性 → Not detected（不打红叉）。  
3) **线性吸光/内滤型**：线性优于或接近 4PL，且 SI 大 → Not detected 或 Detected (caution)（按 ΔAIC/CV 决定）。  
4) **增强型数据**：raw 随浓度上升且满足判据 → Detected（enhancement）。

---

## 11. 给实现者的一句话（给 Claude）
- 在 dose tab 上对 330/350 的 **cold fluorescence vs logC** 做 **线性 vs 4PL** 的模型对决（AIC/BIC + 可选 CV），加一个 **SI（高C是否平台）** 做 QC；多数情况只输出 “Not detected”，Detected 也只给建议性 EC50_app，并对可能线性淬灭给出 caution 提示。
ß