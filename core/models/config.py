#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis Configuration
======================
分析配置模型 - 集中管理所有参数
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from .analysis import AnalysisMethod


class AnalysisConfig(BaseModel):
    """
    分析配置（集中管理所有参数）
    
    设计原则：
    - 所有影响分析结果的参数都在这里定义
    - 便于持久化和重现分析
    - UI 只需要绑定这一个对象
    """
    
    # =========== 基础设置 ===========
    method: AnalysisMethod = Field(
        default=AnalysisMethod.AUC,
        description="Tm 计算方法"
    )
    channel: Literal["ratio", "350", "330"] = Field(
        default="ratio",
        description="数据通道"
    )
    prefer_processed: bool = Field(
        default=False,
        description="优先使用仪器处理后的数据"
    )
    
    # =========== 导数方法参数 ===========
    window_length: int = Field(
        default=21,
        ge=5,
        le=101,
        description="Savitzky-Golay 平滑窗口长度"
    )
    sg_poly_order: int = Field(
        default=2,
        ge=1,
        le=4,
        description="Savitzky-Golay 多项式阶数"
    )
    derivative_peak_method: Literal["find_peaks", "polynomial_fit", "gaussian_deconvolution"] = Field(
        default="find_peaks",
        description="导数峰检测方法"
    )
    
    # =========== AUC 方法参数 ===========
    auc_method: Literal["progress", "derivative"] = Field(
        default="progress",
        description="AUC 计算方法 (progress=TSB归一化, derivative=传统)"
    )
    auc_interpolation_factor: int = Field(
        default=3,
        ge=1,
        le=10,
        description="AUC 插值因子"
    )
    auc_smoothing_window: int = Field(
        default=11,
        ge=5,
        le=51,
        description="AUC 平滑窗口 (仅 derivative 方法)"
    )
    
    # =========== 热力学分析参数 ===========
    # 可行性检查
    min_delta_tm: float = Field(
        default=5.0,
        ge=1.0,
        description="最小 ΔTm 要求 (°C)"
    )
    min_median_r2: float = Field(
        default=0.95,
        ge=0.8,
        le=1.0,
        description="最小中位 TSB R²"
    )
    
    # 等温拟合
    isothermal_slice_step: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="等温切片温度间隔 (°C)"
    )
    min_dynamic_range: float = Field(
        default=20.0,
        ge=10.0,
        le=50.0,
        description="最小动态范围要求 (%)"
    )
    min_4pl_r2: float = Field(
        default=0.95,
        ge=0.8,
        le=1.0,
        description="最小 4PL 拟合 R²"
    )
    use_4pl_fitted_curves: bool = Field(
        default=False,
        description="使用 4PL 拟合曲线构建等温数据集"
    )
    
    # Van't Hoff
    vh_min_points: int = Field(
        default=5,
        ge=3,
        le=20,
        description="Van't Hoff 回归最小点数"
    )
    vh_optimize_low_t: bool = Field(
        default=True,
        description="自动优化低温子集以最大化 R²"
    )
    
    # ΔCp 拟合（可选）
    enable_delta_cp_fitting: bool = Field(
        default=False,
        description="启用 ΔCp 拟合（实验性功能）"
    )
    fixed_delta_cp: Optional[float] = Field(
        default=None,
        description="固定 ΔCp 值 (J/mol/K)，若设置则使用固定值"
    )
    
    # EC50 → KD 转换
    protein_concentration: Optional[float] = Field(
        default=None,
        ge=0,
        description="蛋白浓度 (M)，用于 EC50→KD 转换"
    )
    
    # =========== 显示设置 ===========
    thermodynamic_units: Literal["calorie", "joule"] = Field(
        default="calorie",
        description="热力学参数单位"
    )
    
    class Config:
        validate_assignment = True  # 赋值时自动验证
    
    def get_channel_display(self) -> str:
        """获取通道显示名称"""
        names = {
            "ratio": "350/330 nm Ratio",
            "350": "350 nm",
            "330": "330 nm"
        }
        return names.get(self.channel, self.channel)
    
    def to_cache_key(self) -> str:
        """生成缓存键（用于结果缓存）"""
        import hashlib
        import json
        config_str = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:16]


