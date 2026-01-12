# Export Feature - User Guide
# 导出功能 - 用户指南

**Version**: 0.9.0
**Last Updated**: 2026-01-10

---

## Quick Start
## 快速开始

### Step 1: Run Your Analyses
### 第一步：运行分析

在导出之前，运行您需要的分析：

1. **Basic Analysis** (必需): 上传数据，点击"Run Analysis"
2. **Dose-Response** (可选): 切换到Dose-Response标签页，点击"Run Analysis"
3. **Thermodynamics** (可选): 切换到Thermodynamics标签页，点击"Run Analysis"

> **提示**: 您可以导出任何已完成的分析。未运行的分析会在Excel中显示占位符说明。

---

### Step 2: Click Export
### 第二步：点击导出

在侧边栏底部点击绿色的 **"Export Results"** 按钮。

导出包将自动下载到您的浏览器下载文件夹。

---

## What You Get
## 导出内容

### ZIP Package Structure
### ZIP包结构

```
QuantDSF_Export_20260110_143022.zip
├── QuantDSF_Results.xlsx          # Excel工作簿（4个sheet）
├── Basic_Analysis_1.png           # 融解曲线图（300 DPI）
├── Basic_Analysis_2.png           # Tm分布图
├── Dose_Response_1.png            # 剂量响应曲线
├── Thermodynamics_1.png           # Van't Hoff图
├── Thermodynamics_2.png           # Van't Hoff叠加图
└── Thermodynamics_3.png           # 等温面板图
```

> **注意**: 只有包含数据的图表会被导出。空图表会被自动跳过。

---

## Excel Workbook Details
## Excel工作簿详情

### Sheet 1: Basic_Analysis
**基础分析结果表**

包含所有样本的Tm分析结果：

| 列名 | 描述 | 示例 |
|------|------|------|
| Sample | 样本名称 | BSA |
| Concentration (M) | 浓度（科学计数法） | 3.52E-08 |
| Tm (°C) | 融解温度 | 62.3 |
| Tm Error (°C) | Tm误差 | 0.2 |
| R² | 拟合优度 | 0.998 |
| Method | 分析方法 | BOLTZMANN / AUC / DERIVATIVE |
| QC Status | 质量控制状态 | Pass / Warning / Fail |
| QC Flag | QC标志 | ✅ / ⚠️ / ❌ |
| Source File | 来源文件 | data.pr.pr_files |

**格式化**:
- ✅ 绿色背景 = 通过QC
- ⚠️ 黄色背景 = QC警告
- ❌ 红色背景 = QC失败
- 顶行冻结，便于滚动
- 浓度自动科学计数法

---

### Sheet 2: Dose_Response
**剂量响应分析结果**

单行表格，包含EC50拟合参数：

| 参数 | 描述 | 示例 |
|------|------|------|
| EC50 (M) | 半数有效浓度 | 1.25E-07 |
| EC50 CI Lower (M) | 置信区间下限 | 9.80E-08 |
| EC50 CI Upper (M) | 置信区间上限 | 1.59E-07 |
| R² | 拟合优度 | 0.995 |
| Hill Slope | Hill斜率 | 1.2 |
| Bottom (°C) | 基线Tm | 55.2 |
| Top (°C) | 饱和Tm | 68.5 |
| N Points | 数据点数 | 8 |
| QC Status | 质量描述 | Good fit with 8 points |
| QC Flag | QC标志 | ✅ |

**如果未运行**: 显示提示消息 "No Dose-Response analysis run. Please navigate to Dose-Response tab and run analysis to generate EC50 data."

---

### Sheet 3: Thermodynamics
**热力学分析结果**

参数表格：

| Parameter | Value | Unit | QC Status |
|-----------|-------|------|-----------|
| R² | 0.992 | - | ✅ |
| N Points | 8 | - | |
| ΔH | -28.5 | kcal/mol | |
| ΔS | 28.2 | cal/mol·K | |
| KD (298K / 25°C) | 45.2 | nM | |
| KD (310K / 37°C) | 18.7 | nM | |
| QC Summary | Good Van't Hoff regression | | ✅ |

**单位显示**: 根据您在UI中选择的单位系统（Calorie或Joule）

**如果未运行**: 显示提示消息 "No Thermodynamics analysis run. Please navigate to Thermodynamics tab and run Van't Hoff analysis to generate thermodynamic parameters."

---

### Sheet 4: Analysis_Settings
**分析设置和元数据**

记录所有分析参数，包括：

#### 1. Basic Analysis Settings
- Tm Method: AUC / Boltzmann / Derivative
- Channel: 350nm / 330nm / ratio
- QC Enabled: Yes

#### 2. Dose-Response Settings
- Fitting Method: 4-Parameter Logistic
- QC Enabled: Yes

#### 3. Thermodynamics Settings
- Unit System: Calorie / Joule
- Temperature Slices: 5
- QC Enabled: Yes

#### 4. QC Thresholds
- Minimum R² (Critical): 0.80
- Recommended R²: 0.95
- Minimum Data Points: 3
- Van't Hoff R² (Critical): 0.80

#### 5. Export Metadata
- Export Date: 2026-01-10 14:30:22
- QuantDSF Version: 0.9.0
- Uploaded Files: data.pr.pr_files

---

## Figure Details
## 图表详情

所有图表以 **300 DPI PNG** 格式导出，适合发表：

### Basic_Analysis_1.png
- 所有样本的融解曲线
- 温度范围：20-95°C
- 归一化荧光信号

### Basic_Analysis_2.png
- Tm分布直方图
- 显示所有样本的Tm分布
- 颜色编码（如果多种条件）

### Dose_Response_1.png
- EC50剂量响应曲线
- X轴：浓度（对数刻度）
- Y轴：Tm (°C)
- 包含拟合曲线和数据点

### Thermodynamics_1.png
- Van't Hoff主图
- X轴：1/T (K⁻¹)
- Y轴：ln(KD)
- 线性回归拟合

### Thermodynamics_2.png
- Van't Hoff叠加图
- 等温切片数据点
- 回归线

### Thermodynamics_3.png
- 等温剂量响应面板
- 多个温度切片的4PL拟合
- 用于验证等温拟合质量

---

## Use Cases
## 使用场景

### 1. For Publications
### 发表论文

- 300 DPI图像可直接用于论文插图
- Excel表格数据可用于补充材料
- QC标志帮助筛选高质量数据

**推荐工作流程**:
1. 导出完整包
2. 在Excel中筛选QC=✅的样本
3. 使用PNG图片作为Figure
4. 将Excel数据复制到补充表格

---

### 2. For Data Archiving
### 数据归档

- 单个ZIP包含所有分析结果
- 时间戳文件名便于版本管理
- Analysis_Settings sheet记录所有参数

**文件命名示例**:
- `QuantDSF_Export_20260110_143022.zip` = 2026年1月10日 14:30:22导出

---

### 3. For Collaboration
### 协作共享

- 发送ZIP给同事进行审阅
- 无需重新运行分析
- 所有可视化和数据已打包

---

## Tips and Tricks
## 技巧和提示

### Tip 1: 多次导出
每次导出都会创建唯一的时间戳文件名，不会覆盖之前的导出。您可以：
- 在优化参数后重新导出
- 保留多个版本进行比较
- 为不同的数据集分别导出

### Tip 2: 部分分析导出
您不需要运行所有3种分析。导出功能会：
- 包含您已运行的分析数据
- 为未运行的分析显示占位符说明
- 仅导出包含数据的图表

### Tip 3: QC筛选
在Excel中使用QC Flag列：
- 筛选仅显示 ✅ 的样本
- 调查 ⚠️ 警告样本
- 排除 ❌ 失败样本

### Tip 4: 图表编辑
PNG图表可以在任何图片编辑软件中打开：
- Adobe Illustrator（矢量化处理）
- PowerPoint（组合成panel）
- ImageJ/Fiji（定量分析）

---

## Troubleshooting
## 故障排除

### 问题：下载失败

**原因**: 浏览器阻止了下载
**解决**: 检查浏览器下载设置，允许来自localhost的下载

---

### 问题：Excel打不开

**原因**: 可能的文件损坏
**解决**:
1. 确认文件完整下载（检查文件大小 >100 KB）
2. 使用最新版Microsoft Excel或LibreOffice
3. 尝试重新导出

---

### 问题：图片显示模糊

**原因**: 查看器缩放问题
**解决**: 图片实际是300 DPI。检查图片属性确认尺寸为 1200x800 px @ 300 DPI

---

### 问题：导出包很大

**正常**: 完整导出包（Excel + 6图）通常为 5-15 MB
**如果超过20 MB**: 可能包含大量样本（96孔板），这是正常的

---

## FAQ

**Q: 我可以自定义导出内容吗？**
A: v0.9版本导出所有已运行的分析。未来版本可能支持选择性导出。

**Q: 能导出为PDF吗？**
A: 当前版本仅支持Excel + PNG。PDF导出计划在未来版本中实现。

**Q: 导出的数据精度如何？**
A: Excel中的数值精度与UI显示一致。原始完整精度数据保存在后端。

**Q: 多次导出会覆盖文件吗？**
A: 不会。每次导出都有唯一时间戳文件名。

**Q: 能导出原始数据吗？**
A: 当前版本仅导出分析结果。原始曲线数据导出计划在未来版本实现。

---

## Support

如遇到问题：

1. 查看 [EXPORT_FEATURE_DESIGN.md](EXPORT_FEATURE_DESIGN.md) 了解技术细节
2. 检查 [EXPORT_IMPLEMENTATION_PROGRESS.md](EXPORT_IMPLEMENTATION_PROGRESS.md) 了解已知问题
3. 在GitHub提交Issue: https://github.com/shuozhou87/QuantDSF/issues

---

**Enjoy seamless data export with QuantDSF!**
**祝您使用QuantDSF导出功能愉快！**
