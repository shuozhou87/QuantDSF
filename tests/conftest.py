#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pytest Configuration
=====================
共享的 fixtures 和配置
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 确保能导入项目模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_temperature():
    """生成样本温度数据"""
    return np.linspace(25, 95, 200)


@pytest.fixture
def sample_fluorescence(sample_temperature):
    """生成样本荧光数据 (模拟 Boltzmann 曲线)"""
    T = sample_temperature
    Tm = 55.0
    dT = 5.0
    F_N = 1000
    F_U = 500
    
    F = F_N + (F_U - F_N) / (1.0 + np.exp((Tm - T) / dT))
    # 添加一些噪声
    F += np.random.normal(0, 5, len(F))
    
    return F


@pytest.fixture
def sample_raw_data(sample_temperature, sample_fluorescence):
    """生成样本 RawData"""
    from core.models import RawData
    
    return RawData(
        temperature=sample_temperature.tolist(),
        fluorescence=sample_fluorescence.tolist(),
        channel="ratio"
    )


@pytest.fixture
def sample_config():
    """生成样本分析配置"""
    from core.models import AnalysisConfig
    
    return AnalysisConfig()


