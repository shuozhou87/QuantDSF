# QuantDSF v2 - 整合更新日志

本文档整合了在Windows PC和MacBook Air上的所有更新。

---

## 📅 2025-12-13 更新（MacBook Air）

### 🎯 功能改进

#### 1. ✅ 浓度信息保留功能

**问题**：用户手动输入的浓度信息在切换分析方法时会丢失

**解决方案**：
- 在 `analysis-results-store` 中保存文件名信息
- 通过比较文件名判断是否为同一数据集
- 如果文件名相同，保留用户编辑的浓度信息

**实现位置**：
- `app/callbacks/analysis_callbacks.py` lines 126-129, 264-283, 323

**效果**：
- ✅ 切换分析方法（AUC ↔ TSB ↔ FD）时浓度保留
- ❌ 切换频道时浓度仍会丢失
- 📝 待解决方案详见 `docs/TODO_CONCENTRATION_PERSISTENCE.md`

---

#### 2. ✅ DLS数据自动过滤

**问题**：Prometheus Panta数据集中可能包含DLS（动态光散射）实验数据，这些数据不适用于nanoDSF分析

**解决方案**：
- 在解析ZIP文件后自动过滤掉包含特定关键词的样品
- 关键词：`scattering`, `cumulant radius`, `cumulant_radius`

**实现位置**：
- `app/callbacks/analysis_callbacks.py` lines 175-183

**效果**：
- ✅ DLS相关样品自动从分析结果中排除
- ✅ 避免不相关数据干扰nanoDSF分析

---

#### 3. ✅ 智能颜色映射（无浓度数据时）

**问题**：化合物单点筛选数据没有浓度信息，所有样品被着同一颜色，无区分度

**解决方案**：
- 检测是否有有效的浓度数据
- **有浓度数据**：使用对数浓度梯度颜色映射（蓝→红），图例标题"Concentration"
- **无浓度数据**：每个样品分配不同颜色（均匀分布在蓝→红渐变中），图例标题"Samples"

**实现位置**：
- `app/callbacks/analysis_callbacks.py`
  - Melting Curves: lines 502-607
  - Derivative Curves: lines 634-742

**效果**：
- ✅ 无浓度数据时每个样品有明显的颜色区分
- ✅ 图例标题动态显示"Concentration"或"Samples"
- ✅ 图例显示样品名称而非浓度值

---

### 🐛 已知问题（MacBook Air）

#### 4. ⚠️ FD方法Tm计算偏大（未解决）

**问题描述**：
- FD方法计算的Tm值严重偏大（例如应为50-51°C但计算为59-68°C）
- 差异约 8-17°C
- 图表显示的导数峰值位置与计算的Tm不一致

**测试数据**：BCL2+VCB+PPC compounds (350nm unfolding processed)

**尝试的解决方案**：
- 使用平滑后的导数数据进行峰值检测（而非原始噪声数据）
- 确保Tm计算和图表显示使用相同的平滑数据
- **结果**：问题仍未解决

**实现位置**：
- `app/callbacks/analysis_callbacks.py` lines 218-249

**状态**：
- 🔴 高优先级 - 严重影响FD方法的可用性
- 📝 详细分析见 `docs/TODO_FD_BUGS.md`

**调试工具**：
- 创建了 `debug_fd_tm.py` 用于可视化分析导数峰值检测

**可能的原因**：
1. 峰值检测算法问题（`find_derivative_peaks`）
2. `prominence` 阈值设置不当
3. 温度-索引映射错误
4. 过度平滑导致峰值位置偏移

---

## 📅 2025-12-12 更新（Windows PC）

### 🎯 主要功能实现

#### 1. ✅ Dose-Response EC50 分析功能（全新实现）

**功能描述**：
- 实现了基于 Tm vs Concentration 的 4PL (4-parameter logistic) 拟合计算 EC50
- 这是传统 DSF 方法，尽管物理意义存疑，但在领域内广泛使用

**新增文件**：

**a) `core/analysis/dose_response_ec50.py`**
- `hill4_tm(conc, bottom, top, ec50, hill_slope)`: 4参数logistic函数
  ```python
  Tm = bottom + (top - bottom) * C^n / (EC50^n + C^n)
  ```
- `fit_tm_ec50(concentrations, tm_values, bounds_ec50)`: 4PL曲线拟合
  - 自动尝试多个初始Hill slope值 (0.5, 1.0, 1.5, 2.0) 确保拟合稳定性
  - 计算EC50置信区间（95% CI）使用t分布
  - 返回完整拟合结果：EC50, CI, R², Hill slope, bottom, top

**b) `app/callbacks/dose_response_callbacks.py`**
- `populate_dr_table()`: 填充数据选择表格
  - 自动选择高质量数据点（R² ≥ 0.85且有有效浓度）
  - 显示样品名称、浓度(nM)、Tm、R²、拟合方法、质量标志

- `run_dose_response_analysis()`: 执行EC50分析
  - 从选中数据点提取浓度和Tm
  - 调用4PL拟合
  - 生成dose-response曲线图（对数浓度坐标）
  - 显示EC50、置信区间、R²、拟合参数

**修改文件**：

**c) `app/callbacks/tab_callbacks.py`** (lines 368-451)
- 完全重写 `_create_dose_response_content()` 函数
- 新UI包含：
  - 数据选择表格（可多选）
  - "Calculate EC50" 按钮
  - EC50结果显示卡片
  - Dose-response曲线图
  - 拟合参数表格

**d) `app/callbacks/__init__.py`** (line 23, 29)
- 注册 `register_dose_response_callbacks(app)`

---

### 🐛 Bug修复（Windows PC）

#### 2. ✅ DataTable hidden列配置错误修复

**问题**：
- Dash DataTable不支持 `{"name": "idx", "id": "idx", "hidden": True}` 语法
- 导致前端报错："Invalid component prop `columns[0]` key `hidden` supplied to DataTable"

**解决方案**：
- **不在`columns`中定义隐藏列**，而是只在`data`中保留该字段
- Dash会忽略不在columns中定义的数据字段，实现"隐藏"效果

**修改文件**：

1. **`app/callbacks/tab_callbacks.py`** (lines 255-272)
   - Van't Hoff表格：移除 `{"name": "idx", "id": "idx", "hidden": True}` 行
   - 保持data中的idx字段用于索引映射（因为表格经过浓度排序）

2. **`app/callbacks/tab_callbacks.py`** (lines 391-408)
   - Dose-response表格：同样移除idx列定义

3. **`app/callbacks/dose_response_callbacks.py`** (lines 45-52, 109-118)
   - 移除data中的idx字段（dose-response表格不需要，因为未排序）
   - 直接使用 `selected_rows` 索引映射到原始 `results` 数组

**注意**：
- **Van't Hoff表格**：仍在data中保留idx字段，因为表格按浓度排序后行索引≠原始数据索引
- **Dose-response表格**：不需要idx字段，行索引直接对应原始数据索引

---

#### 3. ✅ Van't Hoff AUC Overlay 颜色渐变修复（之前完成）

**问题**：
- 浓度跨度大（如1nM到10μM）时，线性归一化导致低浓度样品颜色区分度差

**解决方案**：
- 使用**对数尺度归一化**：`(log10(C) - log10(C_min)) / (log10(C_max) - log10(C_min))`
- 确保颜色在浓度梯度上均匀分布

**修改文件**：
- `app/callbacks/thermo_callbacks.py` (overlay图生成部分)

---

## 📁 文件结构总结

```
QuantDSF/
├── core/
│   └── analysis/
│       ├── dose_response_ec50.py      [NEW] EC50拟合核心算法
│       ├── vanthoff.py                 [已存在] Van't Hoff分析
│       └── tm/
│           └── derivative.py           [已存在] FD方法（有bug）
├── app/
│   ├── callbacks/
│   │   ├── __init__.py                 [MODIFIED] 注册dose_response_callbacks
│   │   ├── analysis_callbacks.py       [MODIFIED] 浓度保留、DLS过滤、颜色映射
│   │   ├── tab_callbacks.py            [MODIFIED] Dose-response UI、DataTable修复
│   │   ├── dose_response_callbacks.py  [NEW] Dose-response回调函数
│   │   ├── thermo_callbacks.py         [MODIFIED] Van't Hoff颜色渐变修复
│   │   └── ...
│   └── layouts/
│       └── main_layout.py              [MODIFIED] Basic Analysis固定布局
├── docs/
│   ├── CONSOLIDATED_UPDATES.md         [NEW] 本文档
│   ├── SESSION_UPDATE_2025-12-13.md    [NEW] MacBook更新记录
│   ├── UPDATES-121225.md               [NEW] Windows更新记录
│   ├── TODO_FD_BUGS.md                 [NEW] FD方法bug详细分析
│   ├── TODO_CONCENTRATION_PERSISTENCE.md [NEW] 浓度保留待办
│   ├── TODO_FD_IMPROVEMENT.md          [已存在] TSB解析导数方案
│   ├── BUGFIX_TODO.md                  [已存在]
│   └── ...
├── debug_fd_tm.py                      [NEW] FD调试脚本
└── app_v2.py                           [已存在] 应用入口
```

---

## 🧪 测试状态

### ✅ 已验证功能
1. ✅ Dose-response页面正常加载
2. ✅ DataTable报错已修复，表格可正常显示
3. ✅ 浓度在方法切换时保留
4. ✅ DLS数据自动过滤
5. ✅ 无浓度数据时智能颜色映射

### ⏳ 待测试功能（Windows PC上）
1. Dose-response数据选择功能（多选样品）
2. EC50计算按钮是否正常触发
3. 4PL拟合结果准确性
4. Dose-response曲线图显示
5. Van't Hoff页面是否仍正常工作
6. 浓度保留功能是否在Windows上也正常工作
7. DLS过滤是否在Windows上正常工作

### 🔴 已知问题
1. **FD方法Tm计算偏大** - 高优先级，待修复
2. **频道切换时浓度信息丢失** - 中优先级，有解决方案
3. **TSB解析导数方案未激活** - 中优先级

---

## 🔧 技术细节

### 4PL模型参数（Dose-Response）
- **bottom**: Tm在零浓度时的渐近值
- **top**: Tm在无穷大浓度时的渐近值
- **EC50**: 达到(top-bottom)/2时的配体浓度
- **hill_slope**: Hill系数，描述曲线陡峭程度

### 拟合策略
- 使用 `scipy.optimize.curve_fit`
- 初始猜测：
  - bottom0 = min(Tm)
  - top0 = max(Tm)
  - ec50_0 = median(concentration)
  - hill_slope_0 = [0.5, 1.0, 1.5, 2.0] (多次尝试，选最佳R²)
- 参数边界：
  - EC50: 1e-12 到 1e-2 M
  - Hill slope: 0.1 到 10.0

### 置信区间计算
- 使用t分布：`t.ppf(0.975, df)`
- 标准误差从协方差矩阵提取：`np.sqrt(np.diag(pcov))[2]`

### 颜色映射逻辑
```python
# 有浓度数据
if has_valid_concentrations:
    # 对数归一化
    norm_value = (log10(C) - log10(C_min)) / (log10(C_max) - log10(C_min))
    legend_title = "Concentration"
else:
    # 均匀分布
    norm_value = i / (n_samples - 1)
    legend_title = "Samples"
```

---

## 🚀 部署说明

### Windows PC
```bash
cd "c:\Users\rrssd\OneDrive - UT Health San Antonio\QuantDSF\QuantDSF"
source .venv312/Scripts/activate
python app_v2.py --port 8888
```

### MacBook Air
```bash
cd ~/QuantDSF
source venv/bin/activate
python app_v2.py --port 8050
```

**访问地址**：
- Windows: http://127.0.0.1:8888
- Mac: http://127.0.0.1:8050

**故障排除**：
1. **端口被占用**：
   - Windows: `taskkill //F //IM python.exe`
   - Mac: `pkill -f python`
2. **清除Python缓存**：
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +
   find . -name '*.pyc' -delete
   ```
3. **使用备用端口**：`python app_v2.py --port 9999`

---

## 📝 待办事项（优先级排序）

### 🔴 高优先级
1. [ ] **修复FD方法Tm计算偏大问题**
   - 详见 `docs/TODO_FD_BUGS.md`
   - 使用 `debug_fd_tm.py` 调试
   - 可能需要重写峰值检测逻辑

2. [ ] **在Windows PC上测试dose-response功能**
   - 数据选择
   - EC50计算
   - 曲线图显示

### 🟡 中优先级
3. [ ] **解决频道切换时浓度丢失**
   - 详见 `docs/TODO_CONCENTRATION_PERSISTENCE.md`
   - 推荐方案：智能文件名匹配或简化方案

4. [ ] **激活TSB解析导数方案**
   - 详见 `docs/TODO_FD_IMPROVEMENT.md`
   - 可能帮助解决FD方法问题

### 🟢 低优先级
5. [ ] 添加导出EC50结果功能（CSV/Excel）
6. [ ] 添加EC50拟合质量警告（如R² < 0.9）
7. [ ] 添加残差图用于诊断拟合质量
8. [ ] 添加"清空浓度"按钮

---

## 💡 已知限制

1. **Dose-response EC50物理意义存疑**：这是用Tm对浓度拟合，而非传统的分数结合率对浓度。但这是DSF领域的常规做法。

2. **DataTable隐藏列限制**：Dash不支持真正的"隐藏列"，只能通过不在columns中定义来实现。

3. **浓度单位**：内部计算使用M（摩尔），显示使用nM（纳摩尔）。确保文件名解析正确。

4. **FD方法当前不可靠**：由于Tm计算bug，建议用户使用TSB或AUC方法。

5. **频道切换会丢失浓度**：用户需要在每次切换频道后重新输入浓度（或等待修复）。

---

## 📚 参考资料

- Dash DataTable文档: https://dash.plotly.com/datatable
- 4PL曲线拟合: GraphPad Prism documentation
- Van't Hoff方程: 热力学标准教材
- SciPy curve_fit: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html

---

## 🔄 版本历史

- **v2.1** (2025-12-13): MacBook Air更新 - 浓度保留、DLS过滤、智能颜色映射
- **v2.0** (2025-12-12): Windows PC更新 - Dose-response EC50、DataTable修复、Van't Hoff颜色
- **v1.x**: 初始版本

---

**文档版本**: v2.1
**最后更新**: 2025-12-13
**作者**: Claude + User
**应用版本**: QuantDSF v2.1
