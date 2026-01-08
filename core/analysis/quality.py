#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quality Control
================
数据质量控制工具
"""

import numpy as np
from typing import Dict, Any, List

from ..models import RawData, TmResult


def compute_snr(
    F: np.ndarray,
    baseline_region: int = 10
) -> float:
    """
    计算信噪比 (SNR)
    
    Args:
        F: 荧光数组
        baseline_region: 用于估计噪声的基线区域点数
    
    Returns:
        SNR
    """
    # 信号：动态范围
    signal = np.max(F) - np.min(F)
    
    # 噪声：基线区域的标准差
    noise = np.std(F[:baseline_region])
    
    if noise < 1e-10:
        return float('inf')
    
    return signal / noise


def assess_data_quality(
    data: RawData
) -> Dict[str, Any]:
    """
    评估数据质量
    
    Args:
        data: 原始数据
    
    Returns:
        质量评估结果
    """
    T = data.T
    F = data.F
    
    # 基本检查
    n_points = len(T)
    t_range = T.max() - T.min()
    
    # SNR
    snr = compute_snr(F)
    
    # 检测数据问题
    issues = []
    quality_score = 100.0
    
    if n_points < 50:
        issues.append(f"数据点过少 ({n_points})")
        quality_score -= 20
    
    if t_range < 40:
        issues.append(f"温度范围过窄 ({t_range:.1f}°C)")
        quality_score -= 15
    
    if snr < 5:
        issues.append(f"信噪比过低 (SNR={snr:.1f})")
        quality_score -= 30
    elif snr < 10:
        issues.append(f"信噪比较低 (SNR={snr:.1f})")
        quality_score -= 15
    
    # 检测异常值
    z_scores = np.abs((F - np.mean(F)) / np.std(F))
    n_outliers = np.sum(z_scores > 3)
    if n_outliers > n_points * 0.05:
        issues.append(f"存在较多异常点 ({n_outliers})")
        quality_score -= 10
    
    quality_score = max(0, quality_score)
    
    # 确定级别
    if quality_score >= 80:
        level = "Good"
    elif quality_score >= 60:
        level = "Acceptable"
    elif quality_score >= 40:
        level = "Poor"
    else:
        level = "Bad"
    
    return {
        'score': quality_score,
        'level': level,
        'snr': snr,
        'n_points': n_points,
        't_range': t_range,
        'issues': issues
    }


def check_tm_result_quality(
    result: TmResult,
    min_r2: float = 0.90
) -> List[str]:
    """
    检查 Tm 结果质量
    
    Args:
        result: Tm 结果
        min_r2: 最小 R² 要求
    
    Returns:
        警告信息列表
    """
    warnings = []
    
    if np.isnan(result.tm):
        warnings.append("Tm 计算失败")
        return warnings
    
    if result.r_squared < min_r2:
        warnings.append(f"R² 过低 ({result.r_squared:.3f} < {min_r2})")
    
    if result.tm_error and result.tm_error > 2.0:
        warnings.append(f"Tm 误差较大 (±{result.tm_error:.1f}°C)")
    
    if result.snr and result.snr < 5:
        warnings.append(f"信噪比过低 (SNR={result.snr:.1f})")
    
    return warnings


