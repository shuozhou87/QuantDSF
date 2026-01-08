# V1 analyze_tm_boltzmann vs V2 fit_boltzmann_model 关键差异

## V1 analyze_tm_boltzmann (R² = 0.998)

### 初始参数设置 (lines 252-262):
```python
p0 = [
    F.max(),      # A_N
    0.005,        # alpha
    F.min(),      # D_N
    F.max()*0.8,  # A_D
    0.005,        # beta
    F.min()*1.2,  # D_D
    T_center,     # Tm
    0.3           # k
]
```

### 多组初始参数 (lines 277-281):
```python
initial_params = [
    p0,
    [F.max(), 0.01, F.min(), F.max()*0.9, 0.01, F.min()*1.1, T_center, 0.4],
    [F.max(), 0.003, F.min(), F.max()*0.7, 0.003, F.min()*1.3, T_center, 0.2],
]
```

### 关键特征:
1. **无边界约束** - curve_fit没有使用bounds参数
2. **alpha/beta = 0.005, 0.01, 0.003** - 非常小的值
3. **k = 0.3, 0.4, 0.2** - 较大的steepness初猜
4. **A_N/A_D使用F.max()的倍数** - 动态缩放

---

## V2 _fit_exponential_model (R² = 0.94)

### 初始参数设置 (lines 208-210):
```python
T_med = float(np.median(T))
F_min, F_max = F.min(), F.max()
ig_simple = [0.0, 0.0, F_min, 0.0, 0.0, F_max, T_med, 0.2]
```

### 边界约束 (lines 428-438):
```python
lower_bounds = [
    -F_range, -0.1, F_min - F_range,  # A_N, alpha, D_N
    -F_range, -0.1, F_min - F_range,  # A_D, beta, D_D
    T_min - 10, 0.01                  # Tm, k
]
upper_bounds = [
    F_range, 0.1, F_max + F_range,    # A_N, alpha, D_N
    F_range, 0.1, F_max + F_range,    # A_D, beta, D_D
    T_max + 10, 1.0                   # Tm, k
]
```

### 关键特征:
1. **有严格边界约束** - alpha/beta限制在[-0.1, 0.1]
2. **初猜 A_N/A_D = 0.0** - 没有利用F.max()
3. **初猜 alpha/beta = 0.0** - 完全没有指数分量
4. **k限制在[0.01, 1.0]**

---

## 核心问题

V2的问题在于：
1. **初猜太保守** - A=0, alpha=0意味着退化为常数基线
2. **边界可能限制优化** - V1无边界，优化器有更大自由度
3. **没有使用数据的动态范围** - V1用F.max()*0.8等倍数关系

## 建议修复

将V1的初始化策略移植到V2：
1. 使用V1的initial_params设置
2. 移除或放宽bounds约束
3. 保持V1的多初猜测试策略
