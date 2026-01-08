# Performance Analysis: 200 Samples Scalability

**Date**: 2025-12-13
**Question**: Can PyWebView handle 200 samples? Will desktop app perform well?

## Executive Summary

**答案：可以！** PyWebView不是性能瓶颈。真正的瓶颈在Plotly图表渲染和数据处理，这与PyWebView vs Electron vs 浏览器**无关**。

## 关键理解

### PyWebView vs Electron - 性能本质相同

```
Web应用架构：
┌─────────────────────────────────────┐
│  显示层 (Rendering)                  │
│  ├── Electron: Chromium引擎          │
│  └── PyWebView: Edge WebView2        │  ← 都是Chromium！性能一样！
└─────────────────────────────────────┘
          ↑ 接收HTML/CSS/JavaScript
          │
┌─────────────────────────────────────┐
│  应用层 (Application Logic)          │
│  ├── Dash Server (Flask)             │
│  ├── Plotly.js (图表渲染)            │  ← 真正的性能瓶颈！
│  └── Python计算 (NumPy/SciPy)        │  ← 另一个瓶颈！
└─────────────────────────────────────┘
```

**关键点**：
- Electron打包的是**完整的Chromium**
- PyWebView使用的Edge WebView2**也是Chromium**（微软基于Chromium开发）
- **渲染性能完全一样！** 都是同一个引擎

### 真正的性能瓶颈

#### 1. **Plotly图表渲染** ⚠️ 主要瓶颈

从代码分析 ([analysis_callbacks.py:537-650](../app/callbacks/analysis_callbacks.py#L537-L650))：

```python
def _create_melting_curves_plot(results: list) -> go.Figure:
    """创建熔解曲线图"""
    fig = go.Figure()

    # 每个样品添加一条trace
    for r in results:
        fig.add_trace(go.Scatter(
            x=T,           # ~100个温度点
            y=F,           # ~100个荧光值
            mode='lines',
            name=r['name']
        ))
```

**性能估算（200样品）**：
- 每个样品：~100个数据点
- 200个样品 = 20,000个数据点
- Plotly需要渲染200条独立的曲线
- 每条曲线都是可交互的（hover, click, legend toggle）

**Plotly性能特点**：
- 10-50个trace：流畅 ✅
- 50-100个trace：开始变慢 ⚠️
- 100-200个trace：明显卡顿 ❌
- 200+个trace：非常卡 ❌❌

#### 2. **Python数据处理** - 还好

从代码分析 ([analysis_callbacks.py:200-280](../app/callbacks/analysis_callbacks.py#L200-L280))：

```python
# 对每个样品进行循环
for cap in all_capillaries:  # 200次循环
    T = cap['T']  # ~100个点
    F = cap['F']  # ~100个点

    if method == 'derivative':
        T_deriv, deriv = compute_derivative(T, F)  # SG filter: O(n)
        peaks = find_derivative_peaks(T_deriv, deriv)  # O(n)
    elif method == 'boltzmann':
        result = fit_boltzmann_model(T, F)  # curve_fit: O(n*iterations)
```

**性能估算（200样品）**：
- FD方法：200 × 0.01秒 = **2秒** ✅
- TSB方法：200 × 0.05秒 = **10秒** ⚠️ (curve_fit较慢)
- 总计算时间：可接受

#### 3. **内存使用**

```python
# 每个样品的数据
result_dict = {
    'T': T.tolist(),              # ~100个float = 800 bytes
    'F': F.tolist(),              # ~100个float = 800 bytes
    'progress_curve': deriv.tolist(),  # ~100个float = 800 bytes
    'progress_temperature': T_deriv.tolist(),  # ~100个float = 800 bytes
    # ... 其他元数据
}
```

**内存估算（200样品）**：
- 每个样品：~5KB
- 200个样品：~1MB
- Plotly图表对象：~10-20MB
- 总内存使用：~50-100MB ✅ 完全可接受

## 性能瓶颈详细分析

### 问题1: Plotly渲染200条曲线会卡 ❌

**现象**：
- 图表初始加载缓慢（5-10秒）
- 缩放/平移有延迟
- Hover提示反应慢
- Legend切换卡顿

**根本原因**：
Plotly在浏览器中用JavaScript渲染，200个trace意味着：
- 200个SVG path元素
- 每个path有~100个点
- 每次交互都要重新计算所有元素的位置
- DOM操作开销巨大

**与PyWebView/Electron无关！** 这是Plotly.js本身的限制。

### 问题2: 大量数据传输会慢 ⚠️

**现象**：
- 点击"Run Analysis"后等待时间长
- 图表更新延迟

**根本原因**：
```python
# 所有结果都要转成JSON传给前端
return {
    'results': all_results,  # 200个样品 × ~5KB = 1MB JSON
    ...
}
```

**解决方案**（如果需要）：
- 使用数据采样（每条曲线只显示50个点而不是100个）
- 延迟加载（先显示表格，点击才显示曲线）
- WebGL渲染模式（Plotly支持，性能更好）

## 性能优化方案

### 方案1: 启用Plotly的WebGL渲染 ⭐ 推荐

**修改**：
```python
def _create_melting_curves_plot(results: list) -> go.Figure:
    fig = go.Figure()

    for r in results:
        fig.add_trace(go.Scattergl(  # 改用Scattergl而不是Scatter
            x=T,
            y=F,
            mode='lines',
            name=r['name']
        ))
```

**效果**：
- WebGL硬件加速渲染
- 可以流畅显示1000+条曲线
- **性能提升10-100倍**

**缺点**：
- 某些旧浏览器不支持WebGL（但Edge WebView2支持）
- 导出PDF功能可能受限

### 方案2: 数据采样/抽稀

**修改**：
```python
def _downsample_curve(T, F, max_points=50):
    """如果数据点太多，进行等间隔采样"""
    if len(T) <= max_points:
        return T, F

    indices = np.linspace(0, len(T)-1, max_points, dtype=int)
    return T[indices], F[indices]

# 在绘图时使用
T_plot, F_plot = _downsample_curve(T, F, max_points=50)
fig.add_trace(go.Scatter(x=T_plot, y=F_plot, ...))
```

**效果**：
- 减少数据点数量：100 → 50
- 总数据量减半
- 视觉上几乎看不出差别（曲线仍然平滑）

### 方案3: 分组显示 + 虚拟化

**修改**：
```python
# 默认只显示前50个样品
# 添加"Load More"按钮或分页
# 用户可以选择显示哪些样品
```

**效果**：
- 初始加载快
- 用户可以按需加载

### 方案4: 使用DataShader（终极方案）

**技术**：
- 将数据光栅化为图像
- 不管多少数据点，都渲染成固定大小的图像
- 支持百万级数据点

**缺点**：
- 需要额外的库
- 失去部分交互性（不能hover每条曲线）

## PyWebView vs Electron - 实际性能对比

| 指标 | PyWebView (Edge WebView2) | Electron (Chromium) | 差异 |
|------|---------------------------|---------------------|------|
| **渲染引擎** | Chromium (Edge) | Chromium | **相同** |
| **JavaScript性能** | V8 引擎 | V8 引擎 | **相同** |
| **WebGL支持** | ✅ 支持 | ✅ 支持 | **相同** |
| **Plotly渲染速度** | 相同 | 相同 | **相同** |
| **DOM操作性能** | 相同 | 相同 | **相同** |
| **内存使用** | 稍低（共享系统WebView） | 稍高（独立Chromium） | PyWebView略优 |
| **启动速度** | 稍快 | 稍慢 | PyWebView略优 |
| **文件大小** | 50-80MB | 150-300MB | PyWebView大优 |

**结论**：PyWebView在性能上**不输给**Electron，甚至**略优**（内存和启动速度）。

## 200样品实际性能预测

### 使用当前代码（无优化）

| 操作 | 预计时间 | 体验 |
|------|----------|------|
| 上传200个样品 | 1-2秒 | ✅ 流畅 |
| FD方法分析 | 2-5秒 | ✅ 可接受 |
| TSB方法分析 | 10-15秒 | ⚠️ 稍慢但可接受 |
| 生成Melting Curves图 | 5-10秒 | ⚠️ 慢 |
| 缩放/平移图表 | 1-3秒延迟 | ❌ 卡顿 |
| Hover查看数据 | 0.5-1秒延迟 | ❌ 明显延迟 |

### 使用WebGL优化后

| 操作 | 预计时间 | 体验 |
|------|----------|------|
| 上传200个样品 | 1-2秒 | ✅ 流畅 |
| FD方法分析 | 2-5秒 | ✅ 可接受 |
| TSB方法分析 | 10-15秒 | ⚠️ 稍慢但可接受 |
| 生成Melting Curves图 | 2-3秒 | ✅ 可接受 |
| 缩放/平移图表 | <0.1秒 | ✅ 流畅 |
| Hover查看数据 | <0.1秒 | ✅ 流畅 |

## 建议

### 短期（现在就可以做）

1. **启用WebGL渲染** - 改3行代码，性能提升10倍
   ```python
   go.Scatter → go.Scattergl
   ```

2. **测试实际性能** - 用200个真实样品测试看看
   - 如果不卡，就不需要优化
   - 如果卡，再考虑其他方案

### 长期（如果200样品还不够）

1. **数据采样** - 减少绘图点数
2. **虚拟化/分页** - 不一次性显示所有样品
3. **缓存计算结果** - 避免重复计算

## 关于Desktop App的最终建议

**PyWebView是正确的选择**，因为：

1. **性能相同**：PyWebView用的也是Chromium，性能与Electron一样
2. **文件更小**：50-80MB vs 150-300MB
3. **更简单**：纯Python，不需要学Node.js
4. **更快**：启动速度和内存占用都略优

**性能瓶颈不在显示层**：
- 不管用PyWebView、Electron还是浏览器，Plotly渲染200条曲线都会慢
- 解决方案是**优化Plotly使用方式**（WebGL、采样等），与包装方式无关

**200样品完全可以处理**：
- 计算时间可接受（2-15秒）
- 内存使用正常（~100MB）
- 启用WebGL后图表渲染流畅

## 下一步行动

建议按以下顺序：

1. ✅ **先优化Plotly渲染**（启用WebGL）
2. ✅ **测试200样品性能**（用真实数据）
3. ✅ **如果性能可接受，再做Desktop打包**
4. ⏸️ 如果性能不够，考虑更多优化方案

这样可以确保Desktop版本推出时就已经是优化过的高性能版本。
