# 如何使用Single-Curve热力学分析功能

## 功能位置

新功能在**左侧边栏**的**Advanced Settings**可折叠面板中。

## 详细步骤

### 1. 打开Advanced Settings面板

在左侧边栏中，找到并点击：

```
⚙️ Advanced Settings  [点击展开]
```

这是一个**可折叠的Accordion面板**，默认是折叠状态。您需要点击它来展开。

### 2. 展开后您会看到

展开后会显示两个选项：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ Advanced Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thermodynamic Analysis Method

○ Isothermal Slicing (Van't Hoff) - Requires concentration series  [默认选中]
○ Single-Curve Method (Wright 2017) - Single sample per condition

说明文字：
  Isothermal Slicing: Extracts thermodynamics from concentration-dependent data (≥5 concentrations).
  Single-Curve: Extracts thermodynamics from temperature-dependent unfolding of a single curve.
                Based on Wright et al. 2017 J. Phys. Chem. Lett.

─────────────────────────────────────────

First Derivative Method

☐ Use TSB model for smoothing (experimental)

说明文字：
  When enabled, uses TSB analytical derivative instead of Savitzky-Golay filter.
  ⚠️ Warning: Model-based smoothing may mask complex transitions...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3. 选择Single-Curve方法

点击第二个单选按钮：
```
● Single-Curve Method (Wright 2017) - Single sample per condition
```

### 4. 运行分析

1. 上传您的nanoDSF数据（ZIP文件）
2. 选择Tm计算方法（推荐 **AUC** 或 **TSB**，不建议FD）
3. 确认Advanced Settings中选择了"Single-Curve Method"
4. 点击 **Run Analysis** 按钮

### 5. 查看结果

分析完成后，结果表格会自动添加以下新列：

| 列名 | 含义 |
|------|------|
| **ΔG° (kJ/mol)** | 标准自由能变化（25°C） |
| **ΔH° (kJ/mol)** | 标准焓变 |
| **ΔS° (J/mol·K)** | 标准熵变 |
| **Thermo R²** | ΔG vs T拟合质量 |
| **Thermo** | 质量标志（✓/⚠️/--） |

## 为什么您之前没看到？

原因：**Advanced Settings面板默认是折叠的**！

在sidebar.py第43行：
```python
], start_collapsed=True, className="mb-3"),
```

您需要**主动点击展开**这个面板才能看到里面的选项。

## UI结构

```
左侧边栏
├── 📁 Data Upload
├── ────────────────
├── Analysis Method (AUC/TSB/FD)
├── Channel Selection (350nm/330nm)
├── ────────────────
├── 🔬 Van't Hoff Parameters [可折叠，默认折叠]
├── ⚙️ Advanced Settings [可折叠，默认折叠] ← **新功能在这里！**
│   ├── Thermodynamic Analysis Method
│   │   ○ Isothermal Slicing (默认)
│   │   ○ Single-Curve Method ← **选择这个**
│   └── First Derivative Method
│       ☐ Use TSB model for smoothing
├── ────────────────
└── Run Analysis / Export Data
```

## 快速测试

如果您想快速验证功能是否存在：

1. 打开浏览器访问 http://127.0.0.1:8050
2. 找到左侧边栏
3. 向下滚动，找到 "⚙️ Advanced Settings"
4. 点击展开
5. 您应该能看到 "Thermodynamic Analysis Method" 和两个单选按钮

## 如果还是看不到

请尝试：

1. **刷新浏览器页面**（Ctrl+F5 或 Cmd+Shift+R）
2. **重启应用**：
   ```bash
   # 停止当前运行
   pkill -f app_v2.py

   # 重新启动
   python app_v2.py
   ```

3. **检查代码是否最新**：
   ```bash
   python -c "
   from app.components.sidebar import create_sidebar
   import inspect
   source = inspect.getsource(create_sidebar)
   if 'Advanced Settings' in source:
       print('✓ Advanced Settings 代码存在')
   if 'thermodynamic-method-radio' in source:
       print('✓ Single-Curve选项代码存在')
   "
   ```

## 需要帮助？

如果您仍然无法看到此功能，请告诉我：
1. 您使用的浏览器和版本
2. 是否看到 "⚙️ Advanced Settings" 这个折叠面板
3. 点击后是否能展开
4. 展开后看到了什么内容
