#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Van't Hoff Analysis
====================
Van't Hoff 热力学分析

从 V1 迁移，保持核心算法不变
"""
import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, List, Tuple, Any, Optional
import math

# 常量
R_GAS = 8.314462618  # J/mol/K, 普适气体常数
J_TO_CAL = 0.239006  # 1 J = 0.239006 cal
CAL_TO_J = 4.184     # 1 cal = 4.184 J


def convert_thermodynamic_units(
    delta_h: float, 
    delta_s: float, 
    delta_h_err: float, 
    delta_s_err: float,
    target_units: str
) -> Tuple[float, float, float, float, str, str]:
    """
    转换热力学参数单位
    
    Args:
        delta_h: 焓变 (J/mol)
        delta_s: 熵变 (J/mol/K)
        delta_h_err: 焓变误差
        delta_s_err: 熵变误差
        target_units: 目标单位 ("Calorie" 或 "Joule")
    
    Returns:
        转换后的值和单位字符串
    """
    if target_units == "Calorie":
        delta_h_conv = delta_h * J_TO_CAL / 1000  # J/mol -> kcal/mol
        delta_s_conv = delta_s * J_TO_CAL  # J/mol/K -> cal/mol/K
        delta_h_err_conv = delta_h_err * J_TO_CAL / 1000
        delta_s_err_conv = delta_s_err * J_TO_CAL
        delta_h_unit = "kcal/mol"
        delta_s_unit = "cal/mol/K"
    else:  # Joule (SI units)
        delta_h_conv = delta_h / 1000  # J/mol -> kJ/mol
        delta_s_conv = delta_s  # J/mol/K
        delta_h_err_conv = delta_h_err / 1000
        delta_s_err_conv = delta_s_err
        delta_h_unit = "kJ/mol"
        delta_s_unit = "J/mol/K"
    
    return delta_h_conv, delta_s_conv, delta_h_err_conv, delta_s_err_conv, delta_h_unit, delta_s_unit


def fit_vanthoff(
    T_celsius: np.ndarray,
    KD: np.ndarray,
    delta_cp: Optional[float] = None,
    T_ref: float = 298.15,
    fit_delta_cp: bool = False
) -> Dict[str, Any]:
    """
    拟合 Van't Hoff 方程
    
    标准形式: ln KD = (ΔH/R) * (1/T) - (ΔS/R)
    热容校正形式: ln KD = ΔH₀/RT - ΔS₀/R + (ΔCp/R) × [ln(T/T₀) + (T₀/T - 1)]
    
    Args:
        T_celsius: 温度数组 (°C)
        KD: 解离常数数组 (M)
        delta_cp: 热容变化 (J/mol/K)
        T_ref: 参考温度 (K)
        fit_delta_cp: 是否拟合 ΔCp
    
    Returns:
        拟合结果字典
    """
    T_kelvin = T_celsius + 273.15
    y = np.log(KD)
    n = len(T_kelvin)
    
    if fit_delta_cp:
        return _fit_vanthoff_with_cp(T_kelvin, y, T_ref, n)
    elif delta_cp is not None:
        return _fit_vanthoff_with_fixed_cp(T_kelvin, y, delta_cp, T_ref, n)
    else:
        return _fit_vanthoff_linear(T_kelvin, y, n)


def _fit_vanthoff_linear(T_kelvin: np.ndarray, y: np.ndarray, n: int) -> Dict[str, Any]:
    """标准线性 Van't Hoff 拟合"""
    x = 1.0 / T_kelvin
    A = np.vstack([x, np.ones_like(x)]).T
    coeff, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    a, b = coeff
    
    yfit = a * x + b
    ss_res = np.sum((y - yfit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    
    dof = max(n - 2, 1)
    sigma2 = ss_res / dof
    cov = sigma2 * np.linalg.inv(A.T @ A)
    stderr_a = float(np.sqrt(cov[0, 0]))
    stderr_b = float(np.sqrt(cov[1, 1]))
    
    deltaH = a * R_GAS
    deltaS = -b * R_GAS
    
    return {
        'a': float(a),
        'b': float(b),
        'r2': float(r2),
        'deltaH': float(deltaH),
        'deltaS': float(deltaS),
        'stderr_a': stderr_a,
        'stderr_b': stderr_b,
        'stderr_c': None,
        'n_points': n,
        'delta_cp_used': None,
        'T_ref': None,
        'fit_delta_cp': False,
        'model': 'vh_linear'
    }


def _fit_vanthoff_with_fixed_cp(
    T_kelvin: np.ndarray, 
    y: np.ndarray, 
    delta_cp: float, 
    T_ref: float,
    n: int
) -> Dict[str, Any]:
    """使用固定 ΔCp 的 Van't Hoff 拟合"""
    cp_correction = (delta_cp / R_GAS) * (np.log(T_kelvin / T_ref) + (T_ref / T_kelvin - 1))
    y_corrected = y - cp_correction
    
    x = 1.0 / T_kelvin
    A = np.vstack([x, np.ones_like(x)]).T
    coeff, _, _, _ = np.linalg.lstsq(A, y_corrected, rcond=None)
    a, b = coeff
    
    yfit = a * x + b
    ss_res = np.sum((y_corrected - yfit) ** 2)
    ss_tot = np.sum((y_corrected - np.mean(y_corrected)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    
    dof = max(n - 2, 1)
    sigma2 = ss_res / dof
    cov = sigma2 * np.linalg.inv(A.T @ A)
    stderr_a = float(np.sqrt(cov[0, 0]))
    stderr_b = float(np.sqrt(cov[1, 1]))
    
    deltaH_ref = a * R_GAS
    deltaS_ref = -b * R_GAS
    
    return {
        'a': float(a),
        'b': float(b),
        'r2': float(r2),
        'deltaH': float(deltaH_ref),
        'deltaS': float(deltaS_ref),
        'stderr_a': stderr_a,
        'stderr_b': stderr_b,
        'stderr_c': None,
        'n_points': n,
        'delta_cp_used': float(delta_cp),
        'T_ref': float(T_ref),
        'fit_delta_cp': False,
        'model': 'vh_fixed_cp'
    }


def _fit_vanthoff_with_cp(
    T_kelvin: np.ndarray, 
    y: np.ndarray, 
    T_ref: float,
    n: int
) -> Dict[str, Any]:
    """拟合包含 ΔCp 的 Van't Hoff 模型"""
    g_T = np.log(T_kelvin / T_ref) + (T_ref / T_kelvin - 1)
    x = 1.0 / T_kelvin
    A3 = np.vstack([x, np.ones_like(x), g_T]).T
    
    coeff3, _, _, _ = np.linalg.lstsq(A3, y, rcond=None)
    a3, b3, c3 = coeff3
    yfit3 = A3 @ coeff3
    ss_res3 = np.sum((y - yfit3) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2_3 = 1.0 - ss_res3 / ss_tot if ss_tot > 0 else np.nan
    
    dof3 = max(n - 3, 1)
    sigma2_3 = ss_res3 / dof3
    cov3 = sigma2_3 * np.linalg.inv(A3.T @ A3)
    stderr_a3 = float(np.sqrt(cov3[0, 0]))
    stderr_b3 = float(np.sqrt(cov3[1, 1]))
    stderr_c3 = float(np.sqrt(cov3[2, 2]))
    
    deltaH3 = a3 * R_GAS
    deltaS3 = -b3 * R_GAS
    deltaCp3 = c3 * R_GAS
    
    # 同时拟合线性模型用于模型选择
    A2 = np.vstack([x, np.ones_like(x)]).T
    coeff2, _, _, _ = np.linalg.lstsq(A2, y, rcond=None)
    a2, b2 = coeff2
    yfit2 = A2 @ coeff2
    ss_res2 = np.sum((y - yfit2) ** 2)
    r2_2 = 1.0 - ss_res2 / ss_tot if ss_tot > 0 else np.nan
    
    # 信息准则
    eps = 1e-16
    rss2 = max(ss_res2, eps)
    rss3 = max(ss_res3, eps)
    k2, k3 = 2, 3
    
    aic2 = 2 * k2 + n * math.log(rss2 / n)
    aic3 = 2 * k3 + n * math.log(rss3 / n)
    bic2 = k2 * math.log(n) + n * math.log(rss2 / n)
    bic3 = k3 * math.log(n) + n * math.log(rss3 / n)
    delta_aic = aic2 - aic3
    delta_bic = bic2 - bic3
    
    # QC: 接受 ΔCp 的条件
    T_span_c = float(np.max(T_kelvin) - np.min(T_kelvin))
    enough_span = T_span_c >= 15.0
    enough_points = n >= 12
    strong_ic = (delta_aic >= 10.0) and (delta_bic >= 6.0)
    plausible_max_kcal = 2.5
    plausible = abs(deltaCp3) <= plausible_max_kcal * CAL_TO_J * 1000  # J/mol/K
    
    accept_cp = all([enough_span, enough_points, strong_ic, plausible])
    
    if accept_cp:
        return {
            'a': float(a3),
            'b': float(b3),
            'c': float(c3),
            'r2': float(r2_3),
            'deltaH': float(deltaH3),
            'deltaS': float(deltaS3),
            'deltaCp': float(deltaCp3),
            'stderr_a': stderr_a3,
            'stderr_b': stderr_b3,
            'stderr_c': stderr_c3,
            'n_points': n,
            'delta_cp_used': float(deltaCp3),
            'T_ref': float(T_ref),
            'fit_delta_cp': True,
            'model': 'vh_cp',
            'aic_linear': aic2,
            'bic_linear': bic2,
            'aic_cp': aic3,
            'bic_cp': bic3,
            'delta_aic': delta_aic,
            'delta_bic': delta_bic,
            'cp_qc': {
                'accepted': True,
                'enough_span': enough_span,
                'enough_points': enough_points,
                'strong_ic': strong_ic,
                'plausible': plausible,
                'T_span_K': T_span_c
            }
        }
    else:
        # 回退到线性模型
        dof2 = max(n - 2, 1)
        sigma2_2 = rss2 / dof2
        cov2 = sigma2_2 * np.linalg.inv(A2.T @ A2)
        stderr_a2 = float(np.sqrt(cov2[0, 0]))
        stderr_b2 = float(np.sqrt(cov2[1, 1]))
        deltaH2 = a2 * R_GAS
        deltaS2 = -b2 * R_GAS
        
        return {
            'a': float(a2),
            'b': float(b2),
            'r2': float(r2_2),
            'deltaH': float(deltaH2),
            'deltaS': float(deltaS2),
            'stderr_a': stderr_a2,
            'stderr_b': stderr_b2,
            'stderr_c': None,
            'n_points': n,
            'delta_cp_used': None,
            'T_ref': float(T_ref),
            'fit_delta_cp': True,
            'model': 'vh_linear_fallback',
            'aic_linear': aic2,
            'bic_linear': bic2,
            'aic_cp': aic3,
            'bic_cp': bic3,
            'delta_aic': delta_aic,
            'delta_bic': delta_bic,
            'cp_qc': {
                'accepted': False,
                'enough_span': enough_span,
                'enough_points': enough_points,
                'strong_ic': strong_ic,
                'plausible': plausible,
                'T_span_K': T_span_c
            }
        }


def extrapolate_kd(vanthoff_params: Dict[str, float], T_celsius: float) -> float:
    """
    外推 KD 到指定温度
    
    Args:
        vanthoff_params: Van't Hoff 拟合参数字典
        T_celsius: 目标温度 (°C)
    
    Returns:
        外推的 KD (M)
    """
    T_kelvin = T_celsius + 273.15
    ln_kd = vanthoff_params['a'] * (1.0 / T_kelvin) + vanthoff_params['b']
    
    delta_cp = vanthoff_params.get('delta_cp_used')
    if delta_cp is not None:
        T_ref = vanthoff_params.get('T_ref', 298.15)
        cp_term = (delta_cp / R_GAS) * (np.log(T_kelvin / T_ref) + (T_ref / T_kelvin - 1))
        ln_kd += cp_term
    
    return float(np.exp(ln_kd))


def optimize_low_temp_subset(
    T_celsius: np.ndarray,
    KD: np.ndarray,
    min_points: int = 5,
    exclude_low_kd_ratio: float = 0.1,
    exclude_high_kd_ratio: float = 10.0,
    delta_cp: Optional[float] = None,
    T_ref: float = 298.15,
    fit_delta_cp: bool = False
) -> Tuple[Dict[str, Any], np.ndarray]:
    """
    优化低温子集以最大化 Van't Hoff R²
    
    Args:
        T_celsius: 温度数组
        KD: KD 数组
        min_points: 最小点数
        exclude_low_kd_ratio: 排除低 KD 的比率
        exclude_high_kd_ratio: 排除高 KD 的比率
        delta_cp: 可选的热容项
        T_ref: 参考温度
        fit_delta_cp: 是否拟合 ΔCp
    
    Returns:
        (best_fit, best_mask)
    """
    T = np.array(T_celsius, dtype=float)
    KD_arr = np.array(KD, dtype=float)
    
    # 预过滤极端 KD 值
    median_kd = np.median(KD_arr)
    kd_valid = (KD_arr >= median_kd * exclude_low_kd_ratio) & (KD_arr <= median_kd * exclude_high_kd_ratio)
    
    T_filt = T[kd_valid]
    KD_filt = KD_arr[kd_valid]
    
    if len(T_filt) < min_points:
        T_filt = T
        KD_filt = KD_arr
        kd_valid = np.ones_like(T, dtype=bool)
    
    median_T = float(np.median(T_filt))
    t_min = float(np.min(T_filt)) + 0.5
    t_max = median_T
    
    if t_max - t_min < 1.0 or len(T_filt) < min_points:
        mask_filt = T_filt <= median_T
        if np.sum(mask_filt) < min_points:
            mask_filt = np.ones_like(T_filt, dtype=bool)
        fit = fit_vanthoff(
            T_filt[mask_filt],
            KD_filt[mask_filt],
            delta_cp=delta_cp,
            T_ref=T_ref,
            fit_delta_cp=fit_delta_cp
        )
        
        full_mask = np.zeros_like(T, dtype=bool)
        valid_indices = np.where(kd_valid)[0]
        full_mask[valid_indices[mask_filt]] = True
        return fit, full_mask
    
    # 扫描截断温度
    best_r2 = -np.inf
    best_fit = None
    best_mask_filt = None
    
    for t_cut in np.linspace(t_min, t_max, 24):
        mask_filt = T_filt <= t_cut
        if np.sum(mask_filt) < min_points:
            continue
        
        fit = fit_vanthoff(
            T_filt[mask_filt],
            KD_filt[mask_filt],
            delta_cp=delta_cp,
            T_ref=T_ref,
            fit_delta_cp=fit_delta_cp
        )
        
        if np.isfinite(fit['r2']) and fit['r2'] > best_r2:
            best_r2 = fit['r2']
            best_fit = fit
            best_mask_filt = mask_filt.copy()
    
    if best_fit is None:
        mask_filt = T_filt <= median_T
        if np.sum(mask_filt) < min_points:
            mask_filt = np.ones_like(T_filt, dtype=bool)
        best_fit = fit_vanthoff(
            T_filt[mask_filt],
            KD_filt[mask_filt],
            delta_cp=delta_cp,
            T_ref=T_ref,
            fit_delta_cp=fit_delta_cp
        )
        best_mask_filt = mask_filt
    
    full_mask = np.zeros_like(T, dtype=bool)
    valid_indices = np.where(kd_valid)[0]
    full_mask[valid_indices[best_mask_filt]] = True
    
    return best_fit, full_mask


def assess_extrapolation_reliability(
    T_experimental: np.ndarray,
    T_target: float,
    r2: float,
    n_points: int
) -> Dict[str, Any]:
    """
    评估 Van't Hoff 外推的可靠性
    
    Args:
        T_experimental: 实验温度范围 (K)
        T_target: 外推目标温度 (K)
        r2: Van't Hoff 回归 R²
        n_points: 数据点数
    
    Returns:
        可靠性评估字典
    """
    T_min, T_max = np.min(T_experimental), np.max(T_experimental)
    
    if T_target < T_min:
        extrapolation_distance = T_min - T_target
        extrapolation_type = "below_range"
    elif T_target > T_max:
        extrapolation_distance = T_target - T_max
        extrapolation_type = "above_range"
    else:
        extrapolation_distance = 0
        extrapolation_type = "within_range"
    
    T_range = T_max - T_min
    relative_distance = extrapolation_distance / T_range if T_range > 0 else 0
    
    # 可靠性评分
    reliability_score = 100
    
    if extrapolation_type != "within_range":
        distance_penalty = min(relative_distance * 5, 40)
        reliability_score -= distance_penalty
    
    if r2 < 0.95:
        fit_penalty = (0.95 - r2) * 100
        reliability_score -= fit_penalty
    
    if n_points < 8:
        points_penalty = (8 - n_points) * 5
        reliability_score -= points_penalty
    
    if reliability_score >= 80:
        reliability_level = "High"
        recommendation = "外推结果可靠"
    elif reliability_score >= 60:
        reliability_level = "Medium"
        recommendation = "外推结果可接受，需谨慎使用"
    elif reliability_score >= 40:
        reliability_level = "Low"
        recommendation = "外推结果可疑"
    else:
        reliability_level = "Very Low"
        recommendation = "不建议使用外推结果"
    
    return {
        'reliability_score': max(0, reliability_score),
        'reliability_level': reliability_level,
        'recommendation': recommendation,
        'extrapolation_distance': extrapolation_distance,
        'relative_distance': relative_distance,
        'extrapolation_type': extrapolation_type,
        'T_experimental_range': (T_min, T_max),
        'T_target': T_target,
        'r2': r2,
        'n_points': n_points
    }

