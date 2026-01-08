#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis Result Models
======================
Tm 分析结果数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Tuple
from enum import Enum


class AnalysisMethod(str, Enum):
    """Tm 计算方法枚举"""
    AUC = "auc"
    BOLTZMANN = "boltzmann"
    DERIVATIVE = "derivative"
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            "auc": "AUC (Progress Curve)",
            "boltzmann": "Two-State Boltzmann",
            "derivative": "First Derivative"
        }
        return names.get(self.value, self.value)


class TmResult(BaseModel):
    """Tm 分析结果"""
    
    # 核心结果
    tm: float = Field(
        ..., 
        description="熔解温度 (°C)"
    )
    tm_error: Optional[float] = Field(
        None, 
        description="Tm 标准误差 (°C)"
    )
    r_squared: float = Field(
        ..., 
        description="拟合 R²",
        ge=0,
        le=1
    )
    method: AnalysisMethod = Field(
        ..., 
        description="使用的分析方法"
    )
    
    # 置信区间
    confidence_interval: Optional[Tuple[float, float]] = Field(
        None,
        description="95% 置信区间 (lower, upper)"
    )
    
    # AUC 方法特有
    progress_curve: Optional[List[float]] = Field(
        None,
        description="归一化进度曲线 (0-1)"
    )
    progress_temperature: Optional[List[float]] = Field(
        None,
        description="进度曲线对应温度"
    )
    tsb_r2: Optional[float] = Field(
        None,
        description="TSB 拟合 R²"
    )
    
    # Boltzmann 方法特有
    boltzmann_params: Optional[dict] = Field(
        None,
        description="Boltzmann 拟合参数"
    )
    
    # 导数方法特有
    peak_height: Optional[float] = Field(
        None,
        description="导数峰高度"
    )
    peak_width: Optional[float] = Field(
        None,
        description="导数峰宽度"
    )
    
    # 质量控制
    quality_flag: str = Field(
        "✓",
        description="质量标志"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="警告信息"
    )
    snr: Optional[float] = Field(
        None,
        description="信噪比"
    )
    
    @property
    def is_valid(self) -> bool:
        """结果是否有效"""
        return self.quality_flag == "✓" and self.r_squared >= 0.9
    
    @property
    def ci_lower(self) -> Optional[float]:
        """置信区间下限"""
        return self.confidence_interval[0] if self.confidence_interval else None
    
    @property
    def ci_upper(self) -> Optional[float]:
        """置信区间上限"""
        return self.confidence_interval[1] if self.confidence_interval else None
    
    def to_dict(self) -> dict:
        """转换为字典（用于表格显示）"""
        return {
            'Tm (°C)': f"{self.tm:.1f}",
            'R²': f"{self.r_squared:.3f}",
            'Method': self.method.display_name,
            'Status': self.quality_flag,
        }


