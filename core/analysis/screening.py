#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ΔTm Screening Analysis
=======================
热位移筛选分析
"""

import numpy as np
from typing import List, Optional, Tuple

from ..models import TmResult


def calculate_delta_tm(
    sample_tm: float,
    control_tm: float
) -> float:
    """
    计算 ΔTm
    
    Args:
        sample_tm: 样本 Tm (°C)
        control_tm: 对照 Tm (°C)
    
    Returns:
        ΔTm (°C)
    """
    return sample_tm - control_tm


def calculate_delta_tm_batch(
    tm_results: List[TmResult],
    control_index: int = 0
) -> List[Tuple[float, str]]:
    """
    批量计算 ΔTm
    
    Args:
        tm_results: Tm 结果列表
        control_index: 对照样本索引
    
    Returns:
        List of (ΔTm, 显著性标志) tuples
    """
    if not tm_results:
        return []
    
    control_tm = tm_results[control_index].tm
    
    results = []
    for res in tm_results:
        delta_tm = calculate_delta_tm(res.tm, control_tm)
        
        # 显著性判断
        if delta_tm >= 3.0:
            flag = "⬆️ 显著升高"
        elif delta_tm <= -3.0:
            flag = "⬇️ 显著降低"
        elif abs(delta_tm) >= 1.0:
            flag = "~ 中等变化"
        else:
            flag = ""
        
        results.append((delta_tm, flag))
    
    return results


def filter_significant_hits(
    delta_tm_results: List[Tuple[float, str]],
    threshold: float = 3.0
) -> List[int]:
    """
    筛选显著 hits
    
    Args:
        delta_tm_results: ΔTm 结果列表
        threshold: 显著性阈值 (°C)
    
    Returns:
        显著样本的索引列表
    """
    return [
        i for i, (dtm, _) in enumerate(delta_tm_results)
        if abs(dtm) >= threshold
    ]


