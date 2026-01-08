# 浓度信息保留TODO

## 问题描述
用户手动输入的浓度信息在切换信号频道时会丢失。

## 当前实现状态

### 已实现 ✓
1. **方法切换时保留浓度** (AUC ↔ TSB ↔ FD)
   - 通过比较文件名判断是否同一数据集
   - 如果文件名相同,保留用户编辑的浓度信息
   - 实现位置: `app/callbacks/analysis_callbacks.py` lines 264-283

2. **浓度编辑功能**
   - 表格浓度列可编辑
   - 单位统一为M (摩尔浓度)
   - 编辑后自动更新store
   - 实现位置: `app/callbacks/analysis_callbacks.py` lines 35-67

3. **DLS数据过滤** ✓ (2025-12-12)
   - 过滤掉包含 "scattering" 或 "cumulant radius" 的样品
   - 这些是动态光散射(DLS)实验数据,不适用于nanoDSF分析
   - 实现位置: `app/callbacks/analysis_callbacks.py` lines 175-183

### 未实现问题 ❌

#### 频道切换时浓度信息丢失
- **问题**: 切换信号频道 (ratio ↔ 330nm ↔ 350nm) 时浓度信息会丢失
- **原因**: 频道信息包含在文件名中,切换频道会导致文件名变化
  - 例如: `data_350nm.zip` → `data_330nm.zip`
  - 当前逻辑: 通过 `filenames == prev_filenames` 判断是否同一数据集
  - 结果: 文件名不同 → 被判定为新数据集 → 浓度信息清空

## 解决方案建议

### 方案1: 智能文件名匹配 (推荐)
提取文件名的主要部分,忽略频道后缀:
```python
def extract_base_filename(filename):
    """
    提取文件名主体,移除频道相关后缀
    例如:
    - "data_350nm.zip" → "data"
    - "experiment_ratio.zip" → "experiment"
    """
    # 移除扩展名
    name = filename.rsplit('.', 1)[0]
    # 移除已知的频道后缀
    channel_suffixes = ['_350nm', '_330nm', '_ratio', '_350/330']
    for suffix in channel_suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name
```

**优势**:
- 准确判断是否同一数据集
- 支持频道切换时保留浓度
- 实现相对简单

**劣势**:
- 需要维护频道后缀列表
- 如果文件名格式特殊可能无法正确识别

### 方案2: 基于上传时间戳
在store中记录数据上传时间,只有重新上传时才清空浓度:
```python
# 在 dcc.Upload 的 callback 中设置时间戳
upload_timestamp = time.time()

# 在 run_analysis 中比较时间戳
if previous_timestamp == current_timestamp:
    # 保留浓度
```

**优势**:
- 完全不依赖文件名
- 能准确判断是否重新上传

**劣势**:
- 需要添加额外的timestamp存储
- 需要修改Upload callback

### 方案3: 简化方案 - 永远保留浓度
只要样品名匹配就保留浓度,完全不考虑文件名:
```python
# 简化当前逻辑,移除文件名检查
if previous_results_data and 'results' in previous_results_data:
    previous_results = previous_results_data['results']
    prev_conc_map = {r['name']: r.get('concentration') for r in previous_results}

    for result in all_results:
        if result['name'] in prev_conc_map and prev_conc_map[result['name']] is not None:
            result['concentration'] = prev_conc_map[result['name']]
```

**优势**:
- 实现最简单
- 用户体验最好(浓度永不丢失)

**劣势**:
- 如果用户上传同名但不同的数据集,浓度可能错误保留
- 需要用户手动清除浓度(或刷新页面)

## 推荐实施步骤

1. **短期**: 采用方案3(简化方案)
   - 实现简单,用户体验最好
   - 如果用户需要清空浓度,可以刷新页面或重新上传

2. **中期**: 如果方案3导致问题,采用方案1(智能文件名匹配)
   - 维护常见频道后缀列表
   - 提取文件名主体部分进行比较

3. **长期**: 考虑添加"清空浓度"按钮
   - 让用户可以主动清空所有浓度信息
   - 提供更好的控制

## 相关文件
- `app/callbacks/analysis_callbacks.py`: 主要逻辑
- `app/layouts/main_layout.py`: UI布局

## 更新日志
- 2025-12-12: 初次记录问题,已实现方法切换时保留浓度
- 2025-12-12: 添加DLS数据过滤功能
