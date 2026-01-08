# First Derivative方法改进TODO

## 问题描述
当前FD方法使用Prometheus Panta的processed数据,但导数曲线仍然有明显噪声("狗牙"状),用户观感不佳。

## 尝试过的方案

### 方案1: 两步平滑 (失败)
- 使用更大窗口(51点)平滑原始数据
- 计算导数后再用小窗口(15点)平滑
- **结果**: 导数曲线噪声更大,效果更差

### 方案2: TSB模型解析导数 (未成功实现)
- 理论: 用TSB模型拟合原始数据,然后使用解析导数公式
- 优势: 物理意义明确,导数完全平滑,无数值误差
- **状态**: 代码已实现但未生效,需要调试

**实现位置**:
- `core/analysis/tm/boltzmann.py`: `boltzmann_exp_derivative()` - 解析导数公式
- `core/analysis/tm/derivative.py`: `compute_derivative()` - 调用TSB平滑

**问题**:
- 虽然代码看起来正确,但运行时仍使用传统方法
- 可能的原因:
  1. TSB拟合失败(R² < 0.85)
  2. Exception被静默捕获
  3. 参数提取有问题
  4. 需要添加调试日志确认执行路径

## 当前方案
回退到使用Prometheus Panta的processed数据 + 标准SG滤波器

**优势**:
- 稳定可靠
- 大多数情况下效果可接受

**劣势**:
- 对某些样品(如RPA_SSDNA 4.88E-08 M)导数曲线噪声大
- 用户可能质疑软件质量

## 建议的下一步

### 短期方案
1. 添加调试日志到`compute_derivative()`,确认TSB平滑是否被调用
2. 检查TSB拟合是否成功(打印R²值)
3. 验证参数提取逻辑

### 中期方案
如果TSB解析导数方案可行:
1. 降低R²阈值(从0.85到0.80)以覆盖更多样品
2. 添加用户选项:允许用户选择是否使用TSB平滑
3. 在UI上显示使用了哪种平滑方法

### 长期方案
1. 实现多峰Boltzmann模型的解析导数
2. 对于复杂转变,使用分段拟合
3. 添加自适应平滑参数选择

## 参考资料
- Two-State Boltzmann模型: `core/analysis/tm/boltzmann.py`
- 解析导数推导:
  ```
  F(T) = (1-f_D)*F_N + f_D*F_D
  dF/dT = (1-f_D)*dF_N/dT + f_D*dF_D/dT + df_D/dT*(F_D - F_N)
  ```
- 测试数据集: RPA_SSDNA.zip (特别是4.88E-08 M样品)

## 更新日志
- 2025-12-12: 初次尝试TSB解析导数方案,未成功,暂时回退
