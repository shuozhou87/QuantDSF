#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tm Analysis Methods
====================
Tm 分析方法模块

包含三种 Tm 计算方法:
- AUC (Progress Curve) 法
- Two-State Boltzmann 拟合法
- First Derivative 峰值法
"""

from .boltzmann import (
    boltzmann_exp,
    boltzmann_linear,
    fit_boltzmann_model,
)

from .auc import (
    calc_tm_auc,
)

from .derivative import (
    calculate_tm_derivative,
    compute_derivative,
    find_derivative_peaks,
    smooth_signal,
)

__all__ = [
    # Boltzmann
    'boltzmann_exp',
    'boltzmann_linear',
    'fit_boltzmann_model',
    # AUC
    'calc_tm_auc',
    # Derivative
    'calculate_tm_derivative',
    'compute_derivative',
    'find_derivative_peaks',
    'smooth_signal',
]

