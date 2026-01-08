# QuantDSF v2 - 更新日志

## 2025-12-12 更新

### 🎯 主要功能实现

#### 1. Dose-Response EC50 分析功能（全新实现）

**功能描述**：
- 实现了基于 Tm vs Concentration 的 4PL (4-parameter logistic) 拟合计算 EC50
- 这是传统 DSF 方法，尽管物理意义存疑，但在领域内广泛使用

**新增文件**：

1. **`core/analysis/dose_response_ec50.py`**
   - `hill4_tm(conc, bottom, top, ec50, hill_slope)`: 4参数logistic函数
   - `fit_tm_ec50(concentrations, tm_values, bounds_ec50)`: 4PL曲线拟合
     - 自动尝试多个初始Hill slope值 (0.5, 1.0, 1.5, 2.0) 确保拟合稳定性
     - 计算EC50置信区间（95% CI）使用t分布
     - 返回完整拟合结果：EC50, CI, R², Hill slope, bottom, top

2. **`app/callbacks/dose_response_callbacks.py`**
   - `populate_dr_table()`: 填充数据选择表格
     - 自动选择高质量数据点（R² ≥ 0.85且有有效浓度）
     - 显示样品名称、浓度(nM)、Tm、R²、拟合方法、质量标志

   - `run_dose_response_analysis()`: 执行EC50分析
     - 从选中数据点提取浓度和Tm
     - 调用4PL拟合
     - 生成dose-response曲线图（对数浓度坐标）
     - 显示EC50、置信区间、R²、拟合参数

**修改文件**：

3. **`app/callbacks/tab_callbacks.py`** (lines 368-451)
   - 完全重写 `_create_dose_response_content()` 函数
   - 新UI包含：
     - 数据选择表格（可多选）
     - "Calculate EC50" 按钮
     - EC50结果显示卡片
     - Dose-response曲线图
     - 拟合参数表格

4. **`app/callbacks/__init__.py`** (line 23, 29)
   - 注册 `register_dose_response_callbacks(app)`

---

### 🐛 Bug修复

#### 2. DataTable hidden列配置错误修复

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

#### 3. Van't Hoff AUC Overlay 颜色渐变修复（之前完成）

**问题**：
- 浓度跨度大（如1nM到10μM）时，线性归一化导致低浓度样品颜色区分度差

**解决方案**：
- 使用**对数尺度归一化**：`(log10(C) - log10(C_min)) / (log10(C_max) - log10(C_min))`
- 确保颜色在浓度梯度上均匀分布

**修改文件**：
- `app/callbacks/thermo_callbacks.py` (overlay图生成部分)

---

### 📁 文件结构总结

```
QuantDSF/
├── core/
│   └── analysis/
│       ├── dose_response_ec50.py      [NEW] EC50拟合核心算法
│       ├── vanthoff.py                 [已存在] Van't Hoff分析
│       └── ...
├── app/
│   ├── callbacks/
│   │   ├── __init__.py                 [MODIFIED] 注册dose_response_callbacks
│   │   ├── tab_callbacks.py            [MODIFIED] 重写dose-response页面UI
│   │   ├── dose_response_callbacks.py  [NEW] Dose-response回调函数
│   │   ├── thermo_callbacks.py         [已存在，无需修改]
│   │   └── ...
│   └── ...
└── UPDATES.md                          [NEW] 本文档
```

---

### 🧪 测试状态

#### ✅ 已验证功能
1. Dose-response页面正常加载
2. DataTable报错已修复，表格可正常显示
3. 应用在端口8888成功运行

#### ⏳ 待用户测试
1. 数据选择功能（多选样品）
2. EC50计算按钮是否正常触发
3. 4PL拟合结果准确性
4. Dose-response曲线图显示
5. Van't Hoff页面是否仍正常工作（理论上不受影响）

---

### 🔧 技术细节

#### 4PL模型参数
- **bottom**: Tm在零浓度时的渐近值
- **top**: Tm在无穷大浓度时的渐近值
- **EC50**: 达到(top-bottom)/2时的配体浓度
- **hill_slope**: Hill系数，描述曲线陡峭程度

#### 拟合策略
- 使用 `scipy.optimize.curve_fit`
- 初始猜测：
  - bottom0 = min(Tm)
  - top0 = max(Tm)
  - ec50_0 = median(concentration)
  - hill_slope_0 = [0.5, 1.0, 1.5, 2.0] (多次尝试，选最佳R²)
- 参数边界：
  - EC50: 1e-12 到 1e-2 M
  - Hill slope: 0.1 到 10.0

#### 置信区间计算
- 使用t分布：`t.ppf(0.975, df)`
- 标准误差从协方差矩阵提取：`np.sqrt(np.diag(pcov))[2]`

---

### 🚀 部署说明

**启动应用**：
```bash
cd "c:\Users\rrssd\OneDrive - UT Health San Antonio\QuantDSF\QuantDSF"
source .venv312/Scripts/activate
python app_v2.py --port 8888
```

**访问地址**：
- http://127.0.0.1:8888

**故障排除**：
1. 如果端口被占用，杀掉所有Python进程：`taskkill //F //IM python.exe`
2. 清除Python缓存：`find . -type d -name __pycache__ -exec rm -rf {} +`
3. 使用备用端口：`python app_v2.py --port 9999`

---

### 📝 待办事项

- [ ] 用户测试dose-response功能完整流程
- [ ] 确认Van't Hoff功能未受影响
- [ ] 考虑添加导出EC50结果功能（CSV/Excel）
- [ ] 添加EC50拟合质量警告（如R² < 0.9）
- [ ] 考虑添加残差图用于诊断拟合质量

---

### 💡 已知限制

1. **Dose-response EC50物理意义存疑**：这是用Tm对浓度拟合，而非传统的分数结合率对浓度。但这是DSF领域的常规做法。

2. **DataTable隐藏列限制**：Dash不支持真正的"隐藏列"，只能通过不在columns中定义来实现。这意味着idx字段在用户检查数据时不可见，但可能影响某些高级用法。

3. **浓度单位**：内部计算使用M（摩尔），显示使用nM（纳摩尔）。确保文件名解析正确。

---

### 📚 参考资料

- Dash DataTable文档: https://dash.plotly.com/datatable
- 4PL曲线拟合: GraphPad Prism documentation
- Van't Hoff方程: 热力学标准教材

---

**文档版本**: v1.0
**更新日期**: 2025-12-12
**作者**: Claude + User
**应用版本**: QuantDSF v2
