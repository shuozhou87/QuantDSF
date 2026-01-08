#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Capillary Data Models
=====================
毛细管样本数据模型
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import numpy as np


class RawData(BaseModel):
    """原始温度-荧光数据"""
    
    temperature: List[float] = Field(
        ..., 
        description="温度数组 (°C)",
        min_length=10
    )
    fluorescence: List[float] = Field(
        ..., 
        description="荧光强度数组"
    )
    channel: str = Field(
        ..., 
        description="数据通道 (ratio/350/330)"
    )
    
    @field_validator('fluorescence')
    @classmethod
    def validate_same_length(cls, v, info):
        """验证温度和荧光数组长度一致"""
        if 'temperature' in info.data and len(v) != len(info.data['temperature']):
            raise ValueError('温度和荧光数组长度必须一致')
        return v
    
    @property
    def T(self) -> np.ndarray:
        """温度数组 (numpy)"""
        return np.array(self.temperature)
    
    @property
    def F(self) -> np.ndarray:
        """荧光数组 (numpy)"""
        return np.array(self.fluorescence)
    
    @property
    def n_points(self) -> int:
        """数据点数"""
        return len(self.temperature)
    
    class Config:
        arbitrary_types_allowed = True


class CapillaryData(BaseModel):
    """单个毛细管样本数据"""
    
    id: str = Field(
        ..., 
        description="毛细管标识符 (如 Cap_01)"
    )
    name: str = Field(
        ..., 
        description="样本名称"
    )
    concentration: Optional[float] = Field(
        None, 
        description="配体浓度 (M)",
        ge=0
    )
    raw_data: RawData = Field(
        ..., 
        description="原始数据"
    )
    source_file: str = Field(
        ..., 
        description="来源文件名"
    )
    instrument: Optional[str] = Field(
        None,
        description="仪器类型 (prometheus/tycho)"
    )
    
    @property
    def has_concentration(self) -> bool:
        """是否有浓度信息"""
        return self.concentration is not None and self.concentration > 0
    
    def concentration_str(self) -> str:
        """格式化浓度字符串"""
        if self.concentration is None:
            return "N/A"
        return f"{self.concentration:.2e} M"


