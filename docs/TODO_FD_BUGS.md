# First Derivative方法 - Tm计算错误

## 🔴 严重问题：Tm值严重偏大

### 问题描述

使用First Derivative方法计算Tm时，得到的数值明显偏大，与图表显示不一致。

**测试数据集**：BCL2+VCB+PPC compounds (350nm unfolding processed)

**观察到的现象**：
- FD方法计算的Tm：59.0-68.3°C
- TSB方法计算的Tm：~50-51°C（参考值）
- **图表显示的导数峰值**：明显在50-51°C左右

**差异**：FD方法比实际峰值位置偏大约 **8-17°C**

### 复现步骤

1. 上传BCL2+VCB+PPC数据集
2. 选择First Derivative方法
3. 选择350nm频道
4. 运行分析
5. 观察结果表格中的Tm值（59-68°C）
6. 对比First Derivative Curves图表中的峰值位置（50-51°C）

### 预期行为

FD方法计算的Tm值应该与：
1. 图表上显示的导数峰值位置一致
2. TSB方法计算的Tm值接近（差异应在±2°C以内）

### 可能的原因

#### 1. 峰值检测算法问题

**位置**：`core/analysis/tm/derivative.py` lines 123-181

**嫌疑代码**：
```python
def find_derivative_peaks(T, derivative, method="find_peaks"):
    if method == "find_peaks":
        peaks, properties = find_peaks(-derivative, prominence=0.1 * np.std(derivative))

        if len(peaks) == 0:
            # 如果没找到峰，取绝对值最大的位置
            peak_idx = np.argmin(derivative)  # ⚠️ 可能找到错误的位置
            return [(T[peak_idx], derivative[peak_idx])]
```

**问题分析**：
- `find_peaks` 可能因为 `prominence` 阈值设置不当而找不到峰
- Fallback到 `np.argmin(derivative)` 会找到整个数组中的最小值
- 如果高温区域（60-70°C）有噪声导致的更低值，就会误判为峰值

#### 2. 数据范围问题

**可能性**：
- 导数计算时使用的温度范围可能不正确
- `T_deriv` 数组的索引与 `T` 数组不对应
- 峰值索引映射到温度时出现偏移

#### 3. 平滑参数问题

**当前实现**：
```python
# 第一次平滑：compute_derivative内部
F_smooth = savgol_filter(F, window_length=21, poly_order=2)

# 第二次平滑：用于峰值检测
deriv_smooth = smooth_signal(deriv, window_length=31, poly_order=3)
```

**问题分析**：
- 两次平滑可能导致峰值位置偏移
- 平滑窗口过大（31点）可能使峰值展宽并偏移

### 已尝试的修复方案

#### 尝试1：使用平滑后的导数进行峰值检测 ❌

**修改位置**：`app/callbacks/analysis_callbacks.py` lines 218-249

**修改内容**：
```python
# 之前：使用原始导数
T_deriv, deriv = compute_derivative(T, F)
peaks = find_derivative_peaks(T_deriv, deriv)

# 修改后：使用平滑后的导数
T_deriv, deriv = compute_derivative(T, F)
deriv_smooth = smooth_signal(deriv, window_length=31, poly_order=3)
peaks = find_derivative_peaks(T_deriv, deriv_smooth)
```

**结果**：问题仍未解决，Tm值仍然偏大

**日期**：2025-12-13

### 调试工具

创建了调试脚本 `debug_fd_tm.py` 用于可视化分析：

**功能**：
- 比较原始导数和平滑导数
- 显示 `find_peaks` 找到的所有峰值
- 显示简单最小值检测的结果
- 标注Tm值在原始荧光曲线上的位置

**使用方法**：
```bash
python debug_fd_tm.py <zip_file_path> [sample_name]
```

### 建议的调试步骤

#### 步骤1：验证峰值检测逻辑

1. 运行 `debug_fd_tm.py` 脚本
2. 检查输出：
   - `find_peaks` 找到了几个峰？
   - 最显著的峰在哪个温度？
   - 简单最小值检测的结果是什么？
3. 对比原始导数和平滑导数的峰值位置

#### 步骤2：检查prominence阈值

测试不同的prominence值：
```python
# 当前
prominence=0.1 * np.std(derivative)

# 尝试更小的阈值
prominence=0.05 * np.std(derivative)

# 或使用绝对值
prominence=0.01  # 固定阈值
```

#### 步骤3：验证温度-索引映射

添加日志输出：
```python
peak_idx = np.argmin(derivative)
print(f"Peak index: {peak_idx}")
print(f"T_deriv length: {len(T_deriv)}")
print(f"T_deriv[{peak_idx}] = {T_deriv[peak_idx]}")
print(f"deriv[{peak_idx}] = {derivative[peak_idx]}")
```

#### 步骤4：尝试其他峰值检测方法

使用 `polynomial_fit` 方法：
```python
peaks = find_derivative_peaks(T_deriv, deriv_smooth, method='polynomial_fit')
```

### 临时解决方案

如果无法快速修复，可以考虑：

1. **禁用FD方法**：
   - 从UI中移除FD选项
   - 推荐用户使用TSB方法

2. **降级到简单最小值检测**：
   - 不使用 `find_peaks`
   - 直接用 `np.argmin(derivative)` 找最小值
   - 在峰值附近进行多项式拟合精细化

3. **使用TSB解析导数**：
   - 激活 `use_tsb_smoothing=True` 选项
   - 如果TSB拟合成功，使用解析导数
   - 详见 `TODO_FD_IMPROVEMENT.md`

### 相关文件

- `core/analysis/tm/derivative.py` - FD方法核心逻辑
- `app/callbacks/analysis_callbacks.py` - FD方法调用
- `debug_fd_tm.py` - 调试脚本
- `TODO_FD_IMPROVEMENT.md` - TSB解析导数方案

## ✅ 解决方案（2025-12-15）

### 最终修复方法

**核心问题**：之前的峰值检测使用 `scipy.signal.find_peaks` 在处理负值导数时不够鲁棒，经常因为prominence阈值问题而找不到正确的峰值。

**解决方案**：改用**绝对值最大值检测 + 抛物线精细化**

**修改位置**：`core/analysis/tm/derivative.py` lines 159-195

**关键代码逻辑**：
```python
def find_derivative_peaks(T, derivative, method="find_peaks"):
    if method == "find_peaks":
        # 1. 找到导数绝对值最大的位置（无论正负）
        abs_derivative = np.abs(derivative)
        peak_idx = np.argmax(abs_derivative)
        Tm_simple = T[peak_idx]
        peak_height = derivative[peak_idx]

        # 2. 在峰值附近进行抛物线拟合以获得亚采样精度
        half_width = 3
        start = max(0, peak_idx - half_width)
        end = min(len(T), peak_idx + half_width + 1)

        if end - start >= 3:
            T_local = T[start:end]
            deriv_local = derivative[start:end]

            # 二次多项式拟合: y = ax^2 + bx + c
            coeffs = np.polyfit(T_local, deriv_local, 2)

            # 极值点: x = -b / (2a)
            if coeffs[0] != 0:
                Tm_refined = -coeffs[1] / (2 * coeffs[0])

                # 确保精细化的Tm在合理范围内
                if T_local[0] <= Tm_refined <= T_local[-1]:
                    peak_height_refined = np.polyval(coeffs, Tm_refined)
                    return [(Tm_refined, peak_height_refined)]

        return [(Tm_simple, peak_height)]
```

**为什么有效**：
1. ✅ **绝对值检测更鲁棒**：不依赖prominence参数，直接找到信号变化最剧烈的位置
2. ✅ **抛物线精细化提高精度**：从离散采样中推断连续峰值位置，精度可达小数点后两位
3. ✅ **边界检查确保合理性**：精细化后的Tm必须在局部窗口范围内，避免过拟合
4. ✅ **Fallback机制**：如果抛物线拟合失败，仍返回简单最大值位置

**测试结果**：
- BCL2+VCB+PPC数据集：FD方法Tm值现在与TSB方法一致（~50-51°C）
- 视觉验证：计算的Tm值与First Derivative Curves图表上的峰值位置吻合

### 更新日志

- 2025-12-13: 初次记录问题
- 2025-12-13: 尝试使用平滑导数进行峰值检测（未成功）
- 2025-12-13: 创建调试脚本 `debug_fd_tm.py`
- 2025-12-15: ✅ **问题已解决** - 采用绝对值最大值+抛物线精细化方法

### 优先级

~~🔴 **高优先级** - 严重影响FD方法的可用性~~

✅ **已解决** - FD方法现在可以准确计算Tm值

### 受影响的版本

QuantDSF v2.0 (当前开发版本)

### 测试数据

- BCL2+VCB+PPC compounds (350nm unfolding processed)
- 样品示例：
  - BCL2+VCB+PPC10_0_350 nm_unfolding_processed
  - BCL2+VCB+PPC11_0_350 nm_unfolding_processed
  - BCLXL+VCB+PPC11_0_350 nm_unfolding_processed
