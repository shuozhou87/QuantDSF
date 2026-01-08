# QuantDSF v2 架构设计方案

**创建日期**: 2025-12-11  
**状态**: ✅ 已确认，开始实施

---

## 🎯 设计原则

### 1. **关注点分离 (Separation of Concerns)**
- **核心计算层** (`core/`): 纯 Python，不依赖任何 UI 框架
- **应用层** (`app/`): Dash UI，只负责展示和交互
- **工具层** (`utils/`): 通用工具，可被任何模块调用

### 2. **单一职责原则 (Single Responsibility)**
- 每个模块/文件只做一件事
- 函数不超过 50 行（复杂逻辑拆分）
- 类不超过 200 行

### 3. **依赖方向规则**
```
app/ → core/ → utils/
  ↘      ↓
   → utils/
```
- `core/` 不能导入 `app/`
- `utils/` 不能导入 `core/` 或 `app/`

### 4. **类型安全**
- 使用 Pydantic 数据模型
- 类型提示 (Type Hints) 覆盖率 100%

### 5. **可测试性**
- 核心逻辑必须有单元测试
- UI 和核心逻辑解耦，便于测试

---

## 📁 项目结构

```
QuantDSF/
├── app.py                          # 应用入口点（精简）
├── requirements.txt                # 依赖管理
├── README.md                       # 项目文档
│
├── core/                           # 🔬 核心计算层（纯 Python，无 UI 依赖）
│   ├── __init__.py
│   │
│   ├── models/                     # 数据模型（Pydantic）
│   │   ├── __init__.py
│   │   ├── capillary.py           # CapillaryData, RawData
│   │   ├── analysis.py            # AnalysisResult, TmResult
│   │   ├── thermodynamic.py       # VanHoffResult, EC50Data, ThermodynamicParams
│   │   └── config.py              # AnalysisConfig（集中管理所有参数）
│   │
│   ├── analysis/                   # 分析算法（核心业务逻辑）
│   │   ├── __init__.py
│   │   ├── tm/                     # Tm 计算方法
│   │   │   ├── __init__.py
│   │   │   ├── boltzmann.py       # 两态 Boltzmann 拟合
│   │   │   ├── derivative.py      # 一阶导数分析
│   │   │   └── auc.py             # AUC 进度曲线方法
│   │   │
│   │   ├── thermodynamic/          # 热力学分析
│   │   │   ├── __init__.py
│   │   │   ├── vanthoff.py        # Van't Hoff 回归
│   │   │   ├── isothermal.py      # 等温剂量响应
│   │   │   └── ec50_kd.py         # EC50 → KD 转换
│   │   │
│   │   ├── screening.py            # ΔTm 筛选
│   │   └── quality.py              # 质量控制（SNR, R², 动态范围）
│   │
│   ├── database/                   # 数据持久化（SQLite）
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy ORM 模型
│   │   ├── repository.py          # 数据存取接口
│   │   └── migrations/            # 数据库迁移（可选）
│   │
│   ├── io/                         # 数据输入输出
│   │   ├── __init__.py
│   │   ├── parsers/                # 仪器数据解析
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # BaseParser 抽象类
│   │   │   ├── prometheus.py      # Prometheus NT.48 解析器
│   │   │   └── tycho.py           # Tycho NT.6 解析器
│   │   │
│   │   └── exporters/              # 结果导出
│   │       ├── __init__.py
│   │       ├── csv_exporter.py
│   │       └── excel_exporter.py
│   │
│   └── pipeline.py                 # 分析管道编排（协调各模块）
│
├── app/                            # 🖥️ Dash 应用层
│   ├── __init__.py                # create_app() 工厂函数
│   │
│   ├── layouts/                    # 页面布局（纯 UI 结构）
│   │   ├── __init__.py
│   │   ├── main_layout.py         # 主框架（导航栏、侧边栏、内容区）
│   │   ├── basic_analysis.py      # 基础分析页
│   │   ├── thermodynamic.py       # 热力学分析页
│   │   └── dose_response.py       # 剂量响应页
│   │
│   ├── components/                 # 可复用 UI 组件
│   │   ├── __init__.py
│   │   ├── file_upload.py         # 文件上传组件
│   │   ├── settings_panel.py      # 设置面板组件
│   │   ├── data_table.py          # 数据表格组件
│   │   ├── curve_overlay.py       # 曲线叠加组件
│   │   ├── vanthoff_plot.py       # Van't Hoff 图组件
│   │   └── metrics_display.py     # 指标展示组件
│   │
│   ├── callbacks/                  # 回调函数（交互逻辑）
│   │   ├── __init__.py
│   │   ├── file_callbacks.py      # 文件上传/管理回调
│   │   ├── analysis_callbacks.py  # 分析触发回调
│   │   ├── thermo_callbacks.py    # 热力学分析回调
│   │   └── export_callbacks.py    # 导出功能回调
│   │
│   ├── state.py                    # 集中状态管理
│   └── assets/                     # 静态资源
│       └── custom.css              # 自定义样式
│
├── utils/                          # 🔧 通用工具层
│   ├── __init__.py
│   ├── math_utils.py              # 数学计算工具
│   ├── curve_fitting.py           # 曲线拟合工具（4PL, Boltzmann 等）
│   ├── signal_processing.py       # 信号处理（平滑、导数）
│   ├── validators.py              # 数据验证工具
│   └── formatters.py              # 格式化工具（科学计数法等）
│
├── tests/                          # 🧪 测试
│   ├── __init__.py
│   ├── core/                       # 核心模块测试
│   │   ├── test_tm_analysis.py
│   │   ├── test_vanthoff.py
│   │   └── test_parsers.py
│   └── conftest.py                 # pytest 配置
│
├── docs/                           # 📚 文档
│   ├── V2_ARCHITECTURE_PROPOSAL.md # 本文档
│   └── ...
│
├── _backup_v1/                     # V1 备份（不参与构建）
│
└── SampleDataSets/                 # 测试数据集
```

---

## 🔗 模块依赖关系图

```
                    ┌─────────────┐
                    │   app.py    │  ← 入口点
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    app/     │  ← Dash UI
                    │  layouts/   │
                    │ components/ │
                    │ callbacks/  │
                    └──────┬──────┘
                           │ 调用
                    ┌──────▼──────┐
                    │    core/    │  ← 核心计算
                    │  analysis/  │
                    │    io/      │
                    │  models/    │
                    └──────┬──────┘
                           │ 调用
                    ┌──────▼──────┐
                    │   utils/    │  ← 通用工具
                    └─────────────┘
```

---

## 📦 核心数据模型设计

### 1. `core/models/capillary.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional
import numpy as np

class RawData(BaseModel):
    """原始数据"""
    temperature: List[float] = Field(..., description="温度数组 (°C)")
    fluorescence: List[float] = Field(..., description="荧光强度数组")
    channel: str = Field(..., description="数据通道")
    
    class Config:
        arbitrary_types_allowed = True

class CapillaryData(BaseModel):
    """单个毛细管数据"""
    id: str = Field(..., description="毛细管标识符")
    name: str = Field(..., description="样本名称")
    concentration: Optional[float] = Field(None, description="浓度 (M)")
    raw_data: RawData
    source_file: str = Field(..., description="来源文件")
```

### 2. `core/models/analysis.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class AnalysisMethod(str, Enum):
    AUC = "auc"
    BOLTZMANN = "boltzmann"
    DERIVATIVE = "derivative"

class TmResult(BaseModel):
    """Tm 分析结果"""
    tm: float = Field(..., description="熔解温度 (°C)")
    tm_error: Optional[float] = Field(None, description="Tm 标准误差")
    r_squared: float = Field(..., description="拟合 R²")
    method: AnalysisMethod
    confidence_interval: Optional[tuple[float, float]] = None
    
    # AUC 特有
    progress_curve: Optional[List[float]] = None
    tsb_r2: Optional[float] = None
    
    # 质量标志
    quality_flag: str = Field("✓", description="质量标志")
    warnings: List[str] = Field(default_factory=list)
```

### 3. `core/models/thermodynamic.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class EC50Data(BaseModel):
    """等温 EC50 数据点"""
    temperature: float = Field(..., description="温度 (°C)")
    ec50: float = Field(..., description="EC50 (M)")
    kd: Optional[float] = Field(None, description="KD (M)")
    r_squared: float
    hill_slope: float
    dynamic_range: float
    is_selected: bool = True
    flag: str = ""

class VanHoffResult(BaseModel):
    """Van't Hoff 分析结果"""
    delta_h: float = Field(..., description="ΔH (J/mol)")
    delta_s: float = Field(..., description="ΔS (J/mol/K)")
    delta_cp: Optional[float] = Field(None, description="ΔCp (J/mol/K)")
    r_squared: float
    n_points: int
    
    kd_298k: float = Field(..., description="KD at 298K (M)")
    kd_310k: float = Field(..., description="KD at 310K (M)")
    
    reliability_score_298k: float
    reliability_score_310k: float
    
    # 用于绘图
    fit_slope: float
    fit_intercept: float
```

### 4. `core/models/config.py`

```python
from pydantic import BaseModel, Field
from typing import Literal
from .analysis import AnalysisMethod

class AnalysisConfig(BaseModel):
    """分析配置（集中管理所有参数）"""
    
    # 基础设置
    method: AnalysisMethod = AnalysisMethod.AUC
    channel: Literal["ratio", "350", "330"] = "ratio"
    prefer_processed: bool = False
    
    # 导数方法参数
    window_length: int = Field(21, ge=5, le=101)
    sg_poly_order: int = Field(2, ge=1, le=4)
    derivative_peak_method: str = "find_peaks"
    
    # AUC 方法参数
    auc_method: str = "progress"
    auc_interpolation_factor: int = 3
    
    # 热力学分析参数
    min_delta_tm: float = 5.0
    min_median_r2: float = 0.95
    min_dynamic_range: float = 20.0
    min_4pl_r2: float = 0.95
    vh_min_points: int = 5
    vh_optimize_low_t: bool = True
    
    # 单位
    thermodynamic_units: Literal["calorie", "joule"] = "calorie"
```

---

## 🔄 分析流程编排

### `core/pipeline.py`

```python
from typing import List, Optional
from .models import CapillaryData, TmResult, AnalysisConfig, VanHoffResult
from .analysis.tm import calculate_tm
from .analysis.thermodynamic import run_vanthoff_analysis
from .io.parsers import parse_zip_file

class AnalysisPipeline:
    """分析管道 - 协调各模块"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.capillaries: List[CapillaryData] = []
        self.tm_results: List[TmResult] = []
        self.vanthoff_result: Optional[VanHoffResult] = None
    
    def load_data(self, file_path: str) -> None:
        """加载数据"""
        self.capillaries = parse_zip_file(file_path, self.config.channel)
    
    def run_tm_analysis(self) -> List[TmResult]:
        """运行 Tm 分析"""
        self.tm_results = [
            calculate_tm(cap.raw_data, self.config)
            for cap in self.capillaries
        ]
        return self.tm_results
    
    def run_thermodynamic_analysis(
        self, 
        selected_indices: List[int]
    ) -> VanHoffResult:
        """运行热力学分析"""
        selected_caps = [
            self.capillaries[i] for i in selected_indices
        ]
        self.vanthoff_result = run_vanthoff_analysis(
            selected_caps, 
            self.tm_results,
            self.config
        )
        return self.vanthoff_result
```

---

## 🖥️ Dash 应用结构

### `app/__init__.py`

```python
import dash
from dash import Dash
import dash_bootstrap_components as dbc
from .layouts import create_main_layout
from .callbacks import register_all_callbacks
from .state import AppState

def create_app() -> Dash:
    """应用工厂函数"""
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
        suppress_callback_exceptions=True
    )
    
    app.title = "QuantDSF v2 - nanoDSF Analysis Platform"
    app.layout = create_main_layout()
    
    # 初始化状态
    app.state = AppState()
    
    # 注册回调
    register_all_callbacks(app)
    
    return app
```

### `app/state.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import pandas as pd
from core.models import CapillaryData, TmResult, AnalysisConfig, VanHoffResult

@dataclass
class AppState:
    """集中状态管理"""
    
    # 数据状态
    uploaded_files: List[str] = field(default_factory=list)
    capillaries: List[CapillaryData] = field(default_factory=list)
    
    # 分析状态
    config: AnalysisConfig = field(default_factory=AnalysisConfig)
    tm_results: List[TmResult] = field(default_factory=list)
    vanthoff_result: Optional[VanHoffResult] = None
    
    # UI 状态
    selected_capillary_indices: List[int] = field(default_factory=list)
    selected_ec50_indices: List[int] = field(default_factory=list)
    active_tab: str = "basic"
    
    # 缓存
    _cache: Dict = field(default_factory=dict)
    
    def reset(self) -> None:
        """重置所有状态"""
        self.__init__()
    
    def get_results_df(self) -> pd.DataFrame:
        """获取结果 DataFrame"""
        if not self.tm_results:
            return pd.DataFrame()
        
        return pd.DataFrame([
            {
                'Sample': cap.name,
                'Concentration (M)': cap.concentration,
                'Tm (°C)': res.tm,
                'R²': res.r_squared,
                'Method': res.method.value,
                'Status': res.quality_flag
            }
            for cap, res in zip(self.capillaries, self.tm_results)
        ])
```

---

## ✅ 开发规范

### 1. 文件命名
- 全小写，下划线分隔：`vanthoff_analysis.py`
- 类名：PascalCase：`VanHoffResult`
- 函数名：snake_case：`calculate_tm`

### 2. 导入顺序
```python
# 标准库
import os
from typing import List, Optional

# 第三方库
import numpy as np
import pandas as pd
from pydantic import BaseModel

# 本地模块
from core.models import TmResult
from utils.math_utils import normalize
```

### 3. 文档字符串
```python
def calculate_tm(data: RawData, config: AnalysisConfig) -> TmResult:
    """
    计算熔解温度 (Tm)。
    
    Args:
        data: 原始温度-荧光数据
        config: 分析配置参数
    
    Returns:
        TmResult: 包含 Tm 值和相关质量指标
    
    Raises:
        ValueError: 如果数据点不足或质量太差
    """
```

### 4. 错误处理
```python
# ✅ 好的做法
def parse_concentration(text: str) -> float:
    """解析浓度字符串"""
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"无法解析浓度: '{text}'，请使用科学计数法如 1e-6")

# ❌ 不好的做法
def parse_concentration(text: str) -> float:
    return float(text)  # 裸露的异常
```

---

## 🚀 实施计划

### Phase 1: 基础框架 (Week 1)
- [ ] 创建目录结构
- [ ] 定义核心数据模型 (`core/models/`)
- [ ] 迁移工具函数 (`utils/`)
- [ ] 设置测试框架

### Phase 2: 核心分析 (Week 2-3)
- [ ] 迁移 Tm 分析算法 (`core/analysis/tm/`)
- [ ] 迁移热力学分析 (`core/analysis/thermodynamic/`)
- [ ] 迁移数据解析器 (`core/io/parsers/`)
- [ ] 编写单元测试

### Phase 3: Dash UI (Week 3-4)
- [ ] 创建主布局框架
- [ ] 实现可复用组件
- [ ] 实现回调逻辑
- [ ] 集成测试

### Phase 4: 优化和文档 (Week 5)
- [ ] 性能优化
- [ ] 完善文档
- [ ] 用户测试
- [ ] Bug 修复

---

## 📋 设计决策记录

### ✅ 已确认 (2025-12-11)

| 问题 | 决策 | 备注 |
|------|------|------|
| **数据库支持** | ✅ SQLite | 存储历史分析结果 |
| **多用户支持** | ❌ 暂不需要 | 保留升级可能 |
| **命令行接口** | ❌ 暂不需要 | 有需求时再添加 |
| **ΔCp 拟合** | 可选功能 | 容易过拟合，仅供参考 |
| **Dual Tm 分析** | ❌ 移除 | V1 验证不实用 |
| **三态 Boltzmann** | ❌ 移除 | V1 验证不实用 |

---

**状态**: 架构已确认，开始实施。

