#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Single-Curve Thermodynamic Analysis
====================================
基于Wright et al. 2017方法，从单条melting curve提取热力学参数

参考文献：
Wright, T. A., Stewart, J. M., Page, R. C., & Konkolewicz, D. (2017).
Extraction of Thermodynamic Parameters of Protein Unfolding Using
Parallelized Differential Scanning Fluorimetry.
The Journal of Physical Chemistry Letters, 8(3), 553-558.

核心思想：
1. 从单条DSF曲线归一化得到折叠分数 P_f(T)
2. 计算平衡常数 K_u(T) = (1-P_f) / P_f
3. ΔG(T) = -RT ln(K_u)
4. 线性拟合 ΔG vs T (10-50%解折叠区域)
5. 外推得到ΔG°(298K), ΔH°, ΔS°

简化实现：
- 复用AUC Progress方法的归一化逻辑（baseline fitting）
- 不使用Wright论文中的F_max校正（我们的baseline更可靠）
"""

import numpy as np
from scipy import stats
from typing import Dict, Any, Optional, Tuple
import warnings


def extract_thermodynamics_single_curve(
    T: np.ndarray,
    F: np.ndarray,
    Tm: float,
    progress_curve: Optional[np.ndarray] = None,
    baseline_fold: Optional[np.ndarray] = None,
    baseline_unfold: Optional[np.ndarray] = None,
    min_points: int = 5,
    r2_threshold: float = 0.90
) -> Dict[str, Any]:
    """
    从单条melting curve提取热力学参数 (Wright et al. 2017方法)

    Args:
        T: 温度数组 (K 或 °C)
        F: 荧光强度数组
        Tm: 熔解温度 (与T单位相同)
        progress_curve: 预计算的归一化进度曲线 (0-1)，如果提供则直接使用
        baseline_fold: 折叠态基线（可选，用于归一化）
        baseline_unfold: 解折叠态基线（可选，用于归一化）
        min_points: 线性拟合最少数据点数
        r2_threshold: 线性拟合质量阈值

    Returns:
        {
            'success': bool,
            'delta_G_std': ΔG° at 298K (kJ/mol),
            'delta_H_std': ΔH° (kJ/mol),
            'delta_S_std': ΔS° (kJ/(mol·K)),
            'Tm_used': Tm (K),
            'R_squared': 线性拟合R²,
            'n_points': 拟合数据点数,
            'valid': 是否通过质量控制,
            'warnings': 警告信息列表,
            'fit_data': {
                'T_fit': 拟合使用的温度,
                'delta_G_fit': 拟合使用的ΔG值,
                'P_f': 折叠分数曲线,
                'P_u': 解折叠分数曲线,
                'K_u': 平衡常数曲线
            }
        }
    """
    warnings_list = []

    # 输入验证
    if len(T) != len(F):
        return _failed_result("Temperature and fluorescence arrays must have same length")

    if len(T) < 10:
        return _failed_result("Insufficient data points (need at least 10)")

    if not np.isfinite(Tm):
        return _failed_result("Invalid Tm value")

    # 确保T是Kelvin单位
    T_kelvin = T.copy()
    Tm_kelvin = Tm
    if np.mean(T) < 200:  # 假设是摄氏度
        T_kelvin = T + 273.15
        Tm_kelvin = Tm + 273.15
        warnings_list.append("Converted temperature from °C to K")

    # Step 1: 归一化得到进度曲线 P_f
    if progress_curve is not None:
        # 使用预提供的进度曲线
        P_f = progress_curve
    elif baseline_fold is not None and baseline_unfold is not None:
        # 使用基线计算进度曲线
        denom = baseline_unfold - baseline_fold
        eps = max(1e-12, 1e-9 * np.nanmax(np.abs(denom)))
        denom_safe = np.where(np.abs(denom) < eps, np.sign(denom) * eps + (denom == 0), denom)
        p = (F - baseline_fold) / denom_safe

        # 检查方向
        if np.nanmean(np.diff(p)) < 0:
            p = 1.0 - p

        P_f = 1.0 - np.clip(p, 0.0, 1.0)  # P_f = 1 - P_u
    else:
        # 简单的min-max归一化（fallback）
        F_min = np.min(F)
        F_max = np.max(F)
        if F_max - F_min < 1e-9:
            return _failed_result("No signal variation in fluorescence")

        P_f = (F_max - F) / (F_max - F_min)
        warnings_list.append("Using simple min-max normalization (no baseline provided)")

    # 确保P_f在合理范围内
    P_f = np.clip(P_f, 1e-6, 1 - 1e-6)

    # Step 2: 计算解折叠分数和平衡常数
    P_u = 1.0 - P_f
    K_u = P_u / P_f

    # Step 3: 计算ΔG(T) = -RT ln(K_u)
    R = 8.314  # J/(mol·K)
    delta_G = -R * T_kelvin * np.log(K_u)  # J/mol

    # Step 4: 选择10-50%解折叠区域进行线性拟合
    # Wright论文使用这个范围来避免噪声和聚集影响
    mask = (P_u >= 0.10) & (P_u <= 0.50)

    if np.sum(mask) < min_points:
        # 如果10-50%区域点太少，扩展到5-60%
        mask = (P_u >= 0.05) & (P_u <= 0.60)
        warnings_list.append(f"Expanded fitting range to 5-60% unfolded (insufficient points in 10-50%)")

    T_fit = T_kelvin[mask]
    delta_G_fit = delta_G[mask]

    if len(T_fit) < min_points:
        return _failed_result(
            f"Insufficient data points in unfolding region (found {len(T_fit)}, need {min_points})",
            warnings=warnings_list
        )

    # Step 5: 线性拟合 ΔG = a*T + b
    try:
        slope, intercept, r_value, p_value, std_err = stats.linregress(T_fit, delta_G_fit)
        R_squared = r_value ** 2
    except Exception as e:
        return _failed_result(f"Linear fitting failed: {str(e)}", warnings=warnings_list)

    # Step 6: 提取热力学参数
    # 从线性拟合 ΔG = slope·T + intercept
    # 根据Wright et al. 2017 Equations 7-9:
    #   ΔG = aT + b  (Eq. 7)
    #   ΔG° = b + a·T_standard  (外推到25°C = 298K)
    #   ΔS° = ΔG°/(Tm - T_standard)  (Eq. 8, 注意论文中有负号错误)
    #   ΔH° = Tm·ΔS°  (Eq. 9)
    #
    # 推导: 在Tm处ΔG=0，所以 0 = ΔH° - Tm·ΔS°
    #      在298K处，ΔG° = ΔH° - 298·ΔS°
    #      联立得：ΔS° = ΔG°/(Tm - 298)

    T_standard = 298.15  # K (25°C)
    delta_G_std = slope * T_standard + intercept  # J/mol

    # 根据Eq. 8（修正了符号）
    delta_S_std = delta_G_std / (Tm_kelvin - T_standard)  # J/(mol·K)

    # ΔH° = Tm · ΔS°  (Eq. 9)
    delta_H_std = Tm_kelvin * delta_S_std  # J/mol

    # 转换单位到 kJ/mol
    delta_G_std_kJ = delta_G_std / 1000.0
    delta_H_std_kJ = delta_H_std / 1000.0
    delta_S_std_kJ = delta_S_std / 1000.0

    # Step 7: 质量控制
    valid = True

    if R_squared < r2_threshold:
        warnings_list.append(f"Poor linearity (R²={R_squared:.3f} < {r2_threshold})")
        valid = False

    if not (T_kelvin.min() <= Tm_kelvin <= T_kelvin.max()):
        warnings_list.append(f"Tm ({Tm_kelvin:.1f}K) outside temperature range")
        valid = False

    # 物理合理性检查
    if delta_H_std_kJ < 0:
        warnings_list.append("Negative ΔH° (unfolding should be endothermic)")
        valid = False

    if delta_S_std_kJ < 0:
        warnings_list.append("Negative ΔS° (unfolding should increase entropy)")
        valid = False

    # 典型范围检查（基于文献值）
    if not (10 < delta_G_std_kJ < 150):
        warnings_list.append(f"ΔG° ({delta_G_std_kJ:.1f} kJ/mol) outside typical range (10-150)")

    if not (50 < delta_H_std_kJ < 1000):
        warnings_list.append(f"ΔH° ({delta_H_std_kJ:.1f} kJ/mol) outside typical range (50-1000)")

    if not (0.2 < delta_S_std_kJ < 3.0):
        warnings_list.append(f"ΔS° ({delta_S_std_kJ:.3f} kJ/(mol·K)) outside typical range (0.2-3.0)")

    return {
        'success': True,
        'valid': valid,
        'delta_G_std': delta_G_std_kJ,
        'delta_H_std': delta_H_std_kJ,
        'delta_S_std': delta_S_std_kJ,
        'Tm_used': Tm_kelvin,
        'R_squared': R_squared,
        'n_points': len(T_fit),
        'slope': slope,
        'intercept': intercept,
        'warnings': warnings_list,
        'fit_data': {
            'T_fit': T_fit,
            'delta_G_fit': delta_G_fit / 1000.0,  # kJ/mol for plotting
            'T_all': T_kelvin,
            'delta_G_all': delta_G / 1000.0,
            'P_f': P_f,
            'P_u': P_u,
            'K_u': K_u,
            'fit_range': (P_u.min(), P_u.max())
        }
    }


def _failed_result(error_msg: str, warnings: Optional[list] = None) -> Dict[str, Any]:
    """返回失败结果的标准格式"""
    return {
        'success': False,
        'valid': False,
        'delta_G_std': np.nan,
        'delta_H_std': np.nan,
        'delta_S_std': np.nan,
        'Tm_used': np.nan,
        'R_squared': np.nan,
        'n_points': 0,
        'warnings': warnings if warnings else [],
        'error': error_msg,
        'fit_data': {}
    }


def batch_extract_thermodynamics(
    samples_data: list,
    method: str = 'auto'
) -> Dict[str, Dict[str, Any]]:
    """
    批量提取多个样品的热力学参数

    Args:
        samples_data: 样品数据列表，每个元素包含:
            {
                'name': str,
                'T': np.ndarray,
                'F': np.ndarray,
                'Tm': float,
                'progress_curve': np.ndarray (可选),
                'baseline_fold': np.ndarray (可选),
                'baseline_unfold': np.ndarray (可选)
            }
        method: 'auto', 'with_baseline', 'simple'

    Returns:
        {sample_name: thermodynamic_result_dict}
    """
    results = {}

    for sample in samples_data:
        name = sample.get('name', 'unknown')

        try:
            result = extract_thermodynamics_single_curve(
                T=sample['T'],
                F=sample['F'],
                Tm=sample['Tm'],
                progress_curve=sample.get('progress_curve'),
                baseline_fold=sample.get('baseline_fold'),
                baseline_unfold=sample.get('baseline_unfold')
            )
            results[name] = result
        except Exception as e:
            results[name] = _failed_result(f"Analysis failed: {str(e)}")

    return results


def format_thermodynamic_summary(result: Dict[str, Any], sample_name: str = "") -> str:
    """
    格式化热力学分析结果为可读文本

    Args:
        result: extract_thermodynamics_single_curve的返回值
        sample_name: 样品名称

    Returns:
        格式化的文本摘要
    """
    if not result['success']:
        return f"❌ {sample_name} - Analysis failed: {result.get('error', 'Unknown error')}"

    status = "✓" if result['valid'] else "⚠️"

    lines = []
    if sample_name:
        lines.append(f"{status} {sample_name}")
        lines.append("─" * 50)

    lines.append(f"ΔG°(25°C) = {result['delta_G_std']:>6.1f} ± ? kJ/mol")
    lines.append(f"ΔH°       = {result['delta_H_std']:>6.0f} ± ? kJ/mol")
    lines.append(f"ΔS°       = {result['delta_S_std']:>6.3f} ± ? kJ/(mol·K)")
    lines.append(f"Tm (used) = {result['Tm_used'] - 273.15:>6.1f} °C")
    lines.append(f"R² (ΔG vs T) = {result['R_squared']:.3f} ({result['n_points']} points)")

    if result['warnings']:
        lines.append("")
        lines.append("Warnings:")
        for warning in result['warnings']:
            lines.append(f"  • {warning}")

    return "\n".join(lines)


# 用于测试和验证的辅助函数
def compare_with_literature(
    protein_name: str,
    measured_values: Dict[str, float],
    literature_values: Dict[str, float]
) -> Dict[str, float]:
    """
    比较测量值与文献值

    Args:
        protein_name: 蛋白质名称
        measured_values: {'delta_G_std': float, 'delta_H_std': float, ...}
        literature_values: {'delta_G_std': float, 'delta_H_std': float, ...}

    Returns:
        差异统计
    """
    comparison = {}

    for key in ['delta_G_std', 'delta_H_std', 'delta_S_std']:
        if key in measured_values and key in literature_values:
            measured = measured_values[key]
            literature = literature_values[key]

            if np.isfinite(measured) and np.isfinite(literature) and literature != 0:
                percent_diff = abs(measured - literature) / abs(literature) * 100
                comparison[f'{key}_diff_percent'] = percent_diff
                comparison[f'{key}_diff_abs'] = measured - literature

    return comparison
