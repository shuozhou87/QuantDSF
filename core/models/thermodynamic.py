#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thermodynamic Analysis Models
=============================
热力学分析数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


# 常量
R_GAS = 8.314462618  # J/mol/K, 气体常数
J_TO_CAL = 0.239006  # 1 J = 0.239006 cal
CAL_TO_J = 4.184     # 1 cal = 4.184 J


class EC50Data(BaseModel):
    """等温 EC50 数据点"""
    
    temperature: float = Field(
        ..., 
        description="温度 (°C)"
    )
    ec50: float = Field(
        ..., 
        description="EC50 (M)"
    )
    kd: Optional[float] = Field(
        None, 
        description="KD (M)，经蛋白浓度校正后"
    )
    r_squared: float = Field(
        ...,
        description="4PL 拟合 R²"
    )
    hill_slope: float = Field(
        ...,
        description="Hill 斜率"
    )
    dynamic_range: float = Field(
        ...,
        description="动态范围 (%)"
    )
    bottom: float = Field(
        ...,
        description="4PL 底部"
    )
    top: float = Field(
        ...,
        description="4PL 顶部"
    )
    
    # 质量控制
    is_selected: bool = Field(
        True,
        description="是否被选中用于 Van't Hoff"
    )
    flag: str = Field(
        "",
        description="QC 标志 (⚠️ Low DR / ⚠️ High T 等)"
    )
    
    @property
    def kd_or_ec50(self) -> float:
        """返回 KD（如有）或 EC50"""
        return self.kd if self.kd is not None else self.ec50
    
    @property
    def temperature_kelvin(self) -> float:
        """温度 (K)"""
        return self.temperature + 273.15


class ThermodynamicParams(BaseModel):
    """热力学参数"""
    
    delta_h: float = Field(
        ...,
        description="焓变 ΔH (J/mol)"
    )
    delta_s: float = Field(
        ...,
        description="熵变 ΔS (J/mol/K)"
    )
    delta_cp: Optional[float] = Field(
        None,
        description="热容变化 ΔCp (J/mol/K)"
    )
    
    def delta_h_kcal(self) -> float:
        """ΔH in kcal/mol"""
        return self.delta_h * J_TO_CAL / 1000
    
    def delta_s_cal(self) -> float:
        """ΔS in cal/mol/K"""
        return self.delta_s * J_TO_CAL
    
    def delta_h_kj(self) -> float:
        """ΔH in kJ/mol"""
        return self.delta_h / 1000
    
    def format(self, units: Literal["calorie", "joule"] = "calorie") -> dict:
        """格式化输出"""
        if units == "calorie":
            return {
                'ΔH': f"{self.delta_h_kcal():.1f} kcal/mol",
                'ΔS': f"{self.delta_s_cal():.0f} cal/mol/K",
                'ΔCp': f"{self.delta_cp * J_TO_CAL:.1f} cal/mol/K" if self.delta_cp else "N/A"
            }
        else:
            return {
                'ΔH': f"{self.delta_h_kj():.1f} kJ/mol",
                'ΔS': f"{self.delta_s:.0f} J/mol/K",
                'ΔCp': f"{self.delta_cp:.1f} J/mol/K" if self.delta_cp else "N/A"
            }


class ExtrapolationReliability(BaseModel):
    """外推可靠性评估"""
    
    score: float = Field(
        ...,
        description="可靠性评分 (0-100)",
        ge=0,
        le=100
    )
    level: Literal["High", "Medium", "Low", "Very Low"] = Field(
        ...,
        description="可靠性级别"
    )
    recommendation: str = Field(
        ...,
        description="建议"
    )
    extrapolation_distance: float = Field(
        ...,
        description="外推距离 (°C)"
    )
    is_interpolation: bool = Field(
        ...,
        description="是否为插值（在实验范围内）"
    )


class VanHoffResult(BaseModel):
    """Van't Hoff 分析结果"""
    
    # 回归参数
    slope: float = Field(
        ...,
        description="Van't Hoff 斜率 (a)"
    )
    intercept: float = Field(
        ...,
        description="Van't Hoff 截距 (b)"
    )
    r_squared: float = Field(
        ...,
        description="回归 R²"
    )
    n_points: int = Field(
        ...,
        description="使用的数据点数"
    )
    
    # 热力学参数
    thermodynamics: ThermodynamicParams = Field(
        ...,
        description="热力学参数"
    )
    
    # 标准误差
    slope_stderr: float = Field(
        ...,
        description="斜率标准误差"
    )
    intercept_stderr: float = Field(
        ...,
        description="截距标准误差"
    )
    
    # 外推结果
    kd_298k: float = Field(
        ...,
        description="KD at 298K (25°C) (M)"
    )
    kd_310k: float = Field(
        ...,
        description="KD at 310K (37°C) (M)"
    )
    
    # 可靠性评估
    reliability_298k: ExtrapolationReliability = Field(
        ...,
        description="298K 外推可靠性"
    )
    reliability_310k: ExtrapolationReliability = Field(
        ...,
        description="310K 外推可靠性"
    )
    
    # 实验范围
    t_min: float = Field(
        ...,
        description="最低实验温度 (°C)"
    )
    t_max: float = Field(
        ...,
        description="最高实验温度 (°C)"
    )
    
    # ΔCp 相关（可选功能）
    delta_cp_fitted: Optional[float] = Field(
        None,
        description="拟合的 ΔCp (J/mol/K)"
    )
    model_used: Literal["linear", "with_cp"] = Field(
        "linear",
        description="使用的模型"
    )
    aic_linear: Optional[float] = Field(None, description="线性模型 AIC")
    aic_cp: Optional[float] = Field(None, description="ΔCp 模型 AIC")
    
    def format_kd(self, temperature: Literal["298K", "310K"]) -> str:
        """格式化 KD 值"""
        kd = self.kd_298k if temperature == "298K" else self.kd_310k
        return f"{kd:.2e} M"


