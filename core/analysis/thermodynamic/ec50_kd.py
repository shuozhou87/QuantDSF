#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EC50 to KD Conversion
======================
EC50 到 KD 的转换

使用 Morrison 方程处理紧密结合情况
从 V1 迁移，保持核心算法不变
"""
import numpy as np
from typing import List, Dict, Any


def convert_ec50_to_kd(
    ec50_array: np.ndarray,
    protein_conc: float,
    stoichiometry: float = 1.0
) -> np.ndarray:
    """
    使用 Morrison 方程将 EC50 转换为 KD
    
    对于 1:1 结合平衡:
    - [Protein] << KD: EC50 ≈ KD (弱结合近似)
    - [Protein] >> KD: EC50 ≈ KD + [Protein]/2 (紧密结合)
    - 一般情况: 使用 Morrison 二次方程
    
    Args:
        ec50_array: EC50 值数组 (M)
        protein_conc: 总蛋白浓度 (M)
        stoichiometry: 结合化学计量比 (默认 1:1)
    
    Returns:
        KD 值数组 (M)
    
    参考文献:
        Morrison, J. F. (1969). Biochim. Biophys. Acta, 185, 269-286.
        Huang, X. (2003). J. Biomol. Screen., 8(1), 34-38.
    """
    """
    使用 Morrison 方程统一转换（不再分弱/紧密结合分支，避免“未转换”情况）
    """
    kd_array = np.zeros_like(ec50_array, dtype=float)
    if protein_conc is None or protein_conc <= 0:
        return ec50_array.astype(float)

    for i, ec50 in enumerate(ec50_array):
        if ec50 is None or ec50 <= 0:
            kd_array[i] = np.nan
            continue
        # Morrison 二次方程：KD² + KD*EC50 - [P]*EC50/stoich = 0
        a = 1.0
        b = ec50
        c = -protein_conc * ec50 / max(stoichiometry, 1e-12)
        discriminant = b ** 2 - 4 * a * c
        if discriminant < 0:
            kd_array[i] = ec50
            continue
        kd_solution = (-b + np.sqrt(discriminant)) / (2 * a)
        # 确保正值；若异常则回退 EC50
        kd_array[i] = kd_solution if kd_solution > 0 else ec50

    return kd_array


def update_ec50_data_with_kd(
    ec50_data: List[Dict[str, Any]],
    protein_conc: float,
    stoichiometry: float = 1.0
) -> List[Dict[str, Any]]:
    """
    更新 EC50 数据列表，添加 KD 值
    
    Args:
        ec50_data: EC50 数据字典列表
        protein_conc: 蛋白浓度 (M)
        stoichiometry: 化学计量比
    
    Returns:
        添加了 KD 字段的数据列表
    """
    if not ec50_data or protein_conc is None:
        return ec50_data
    
    ec50_values = np.array([d['EC50'] for d in ec50_data])
    kd_values = convert_ec50_to_kd(ec50_values, protein_conc, stoichiometry)
    
    for i, data in enumerate(ec50_data):
        data['KD'] = float(kd_values[i])
        data['protein_conc'] = protein_conc
        data['binding_regime'] = _determine_binding_regime(ec50_values[i], protein_conc)
    
    return ec50_data


def _determine_binding_regime(ec50: float, protein_conc: float) -> str:
    """判断结合区域"""
    if protein_conc < 0.1 * ec50:
        return "weak"
    elif protein_conc > 10 * ec50:
        return "tight"
    else:
        return "intermediate"

