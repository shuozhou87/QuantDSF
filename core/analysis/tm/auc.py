#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AUC-based Tm Calculation
=========================
基于曲线下面积的 Tm 计算方法

从 V1 迁移，保持核心算法不变
"""
import numpy as np
from scipy.interpolate import interp1d
from scipy.stats import t as t_dist
from typing import Dict, Any, Optional, Tuple

# scipy 兼容性处理
try:
    from scipy.integrate import cumulative_trapezoid as cumtrapz
except ImportError:
    from scipy.integrate import cumtrapz

from ...utils import smooth_signal
from .boltzmann import fit_boltzmann_model, boltzmann_exp


def calc_tm_auc(
    T: np.ndarray, 
    F: np.ndarray, 
    method: str = 'derivative',
    baseline_correction: bool = True,
    smoothing_window: int = 11,
    interpolation_factor: int = 3
) -> Dict[str, Any]:
    """
    使用曲线下面积 (AUC) 方法计算 Tm
    
    AUC 方法确定 Tm 为达到总导数面积 50% 时的温度。
    相比峰值查找方法，对噪声更不敏感。
    
    Args:
        T: 温度数组
        F: 荧光数组
        method: 分析方法 ('derivative' 或 'progress')
        baseline_correction: 是否应用基线校正
        smoothing_window: 平滑窗口大小
        interpolation_factor: 插值因子
    
    Returns:
        包含 Tm_AUC、质量指标等的结果字典
    """
    if len(T) != len(F) or len(T) < 10:
        return {
            'success': False,
            'Tm_AUC': np.nan,
            'total_area': np.nan,
            'area_50_percent': np.nan,
            'quality_score': 0.0,
            'error': '数据点不足'
        }
    
    try:
        # 移除 NaN 值
        valid_mask = np.logical_and(np.isfinite(T), np.isfinite(F))
        T_clean = T[valid_mask]
        F_clean = F[valid_mask]
        
        if len(T_clean) < 10:
            return {
                'success': False,
                'Tm_AUC': np.nan,
                'total_area': np.nan,
                'area_50_percent': np.nan,
                'quality_score': 0.0,
                'error': '有效数据点过少'
            }
        
        # 按温度排序
        sort_idx = np.argsort(T_clean)
        T_sorted = T_clean[sort_idx]
        F_sorted = F_clean[sort_idx]
        
        if method == 'derivative':
            return _calc_tm_auc_derivative(
                T_sorted, F_sorted, baseline_correction,
                smoothing_window, interpolation_factor
            )
        elif method in ('direct', 'progress'):
            return _calc_tm_auc_progress(T_sorted, F_sorted, interpolation_factor)
        else:
            return {
                'success': False,
                'Tm_AUC': np.nan,
                'total_area': np.nan,
                'area_50_percent': np.nan,
                'quality_score': 0.0,
                'error': f'不支持的 AUC 方法: {method}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'Tm_AUC': np.nan,
            'total_area': np.nan,
            'area_50_percent': np.nan,
            'quality_score': 0.0,
            'error': str(e)
        }


def _calc_tm_auc_derivative(
    T: np.ndarray, 
    F: np.ndarray,
    baseline_correction: bool,
    smoothing_window: int,
    interpolation_factor: int
) -> Dict[str, Any]:
    """使用导数方法计算 AUC Tm"""
    
    F_smooth = smooth_signal(F, smoothing_window)
    dF_dT = np.gradient(F_smooth, T)
    
    if baseline_correction:
        dF_dT = _apply_baseline_correction(T, dF_dT)
    
    if interpolation_factor > 1:
        T_interp, dF_dT_interp = _interpolate_data(T, dF_dT, interpolation_factor)
    else:
        T_interp, dF_dT_interp = T, dF_dT
    
    cumulative_area = cumtrapz(np.abs(dF_dT_interp), T_interp, initial=0)
    total_area = cumulative_area[-1]
    
    if total_area == 0:
        return {
            'success': False,
            'Tm_AUC': np.nan,
            'total_area': 0.0,
            'area_50_percent': 0.0,
            'quality_score': 0.0,
            'error': '总面积为零'
        }
    
    target_area = total_area * 0.5
    idx_50 = np.argmin(np.abs(cumulative_area - target_area))
    Tm_AUC = T_interp[idx_50]
    
    quality_score = _calculate_auc_quality(T_interp, dF_dT_interp, cumulative_area, total_area)
    
    return {
        'success': True,
        'Tm_AUC': Tm_AUC,
        'total_area': total_area,
        'area_50_percent': target_area,
        'cumulative_area': cumulative_area,
        'temperature_range': T_interp,
        'derivative_curve': dF_dT_interp,
        'quality_score': quality_score,
        'method': 'derivative'
    }


def _calc_tm_auc_progress(
    T: np.ndarray, 
    F: np.ndarray, 
    interpolation_factor: int
) -> Dict[str, Any]:
    """使用进度曲线方法计算 AUC Tm"""
    
    baseline_mode = 'exponential'
    F_fold = None
    F_unfold = None
    r2 = np.nan
    popt = None
    Tm_tsb = np.nan
    
    raw_ptp = float(np.ptp(F))
    tsb_r2 = np.nan
    denom_ptp = np.nan

    # 优先使用 V1 风格的两段线性基线（首尾各 15%），减少指数拟合不收敛问题
    try:
        n_seg = max(5, int(len(T) * 0.15))
        T_native = T[:n_seg]
        F_native = F[:n_seg]
        T_denat = T[-n_seg:]
        F_denat = F[-n_seg:]
        # 线性拟合首尾
        coef_nat = np.polyfit(T_native, F_native, 1)
        coef_den = np.polyfit(T_denat, F_denat, 1)
        F_fold = coef_nat[0] * T + coef_nat[1]
        F_unfold = coef_den[0] * T + coef_den[1]
        denom_ptp = float(np.ptp(F_unfold - F_fold))
        tsb_r2 = 1.0  # 线性基线视为确定性
        Tm_tsb = np.nan
    except Exception:
        F_fold = None
        F_unfold = None
        Tm_tsb = np.nan

    # 若线性基线失败，再尝试指数/线性 Boltzmann 拟合（作为补充）
    if F_fold is None or F_unfold is None:
        try:
            fit_result = fit_boltzmann_model(T, F, model='exponential', prefer_linear=True)
            if fit_result and fit_result.get('success'):
                popt = [
                    fit_result['parameters']['A_N'],
                    fit_result['parameters'].get('alpha', 0.0),
                    fit_result['parameters']['D_N'],
                    fit_result['parameters']['A_D'],
                    fit_result['parameters'].get('beta', 0.0),
                    fit_result['parameters']['D_D'],
                    fit_result['parameters']['Tm'],
                    fit_result['parameters']['k']
                ]
                Tm_tsb = fit_result['Tm']
                tsb_r2 = fit_result['R_squared']
                
                A_N, alpha, D_N, A_D, beta, D_D = popt[:6]
                F_fold = A_N * np.exp(alpha * T) + D_N
                F_unfold = A_D * np.exp(beta * T) + D_D
                denom_ptp = float(np.ptp(F_unfold - F_fold))
        except Exception:
            pass
    
    # 回退逻辑：基线缺失或被标记异常时走导数/最简归一化
    if F_fold is None or F_unfold is None:
        # 保留导数法求 Tm，但为 overlay 提供 min-max 进度，避免空曲线
        deriv_result = _calc_tm_auc_derivative(
            T, F,
            baseline_correction=True,
            smoothing_window=11,
            interpolation_factor=interpolation_factor if interpolation_factor else 3
        )
        # 附加 min-max 归一化的进度，用于可视化
        if raw_ptp > 0:
            p_minmax = (F - F.min()) / raw_ptp
            deriv_result['progress_curve'] = p_minmax
            deriv_result['temperature_range'] = T
        deriv_result['method'] = 'derivative_fallback'
        deriv_result['tsb_r2'] = tsb_r2
        deriv_result['tsb_denom_ptp'] = denom_ptp
        return deriv_result
    
    # 计算进度曲线
    denom = (F_unfold - F_fold)
    eps = max(1e-12, 1e-9 * np.nanmax(np.abs(denom)))
    denom_safe = np.where(np.abs(denom) < eps, np.sign(denom) * eps + (denom == 0), denom)
    
    p = (F - F_fold) / denom_safe
    
    if np.nanmean(np.diff(p)) < 0:
        p = 1.0 - p
    
    p = np.clip(p, 0.0, 1.0)
    
    # 插值
    if interpolation_factor and interpolation_factor > 1:
        T_interp, p_interp = _interpolate_data(T, p, interpolation_factor)
        p_interp = np.clip(p_interp, 0.0, 1.0)
    else:
        T_interp, p_interp = T, p
    
    # 使用转变窗口查找中点
    transition_mask = (p_interp >= 0.2) & (p_interp <= 0.8)
    transition_indices = np.where(transition_mask)[0]
    
    if len(transition_indices) > 10:
        p_transition = p_interp[transition_mask]
        T_transition = T_interp[transition_mask]
        idx_in_transition = int(np.argmin(np.abs(p_transition - 0.5)))
        Tm_midpoint = T_transition[idx_in_transition]
    else:
        idx = int(np.argmin(np.abs(p_interp - 0.5)))
        Tm_midpoint = T_interp[idx]
    
    # Hill 方程拟合
    Tm_hill, hill_fit_success, hill_r2, hill_params, hill_pcov, hill_sample_size, hill_fit_curve = \
        _fit_hill_equation_tm(T_interp, p_interp)
    
    # 处理 Hill 拟合结果
    hill_bottom = hill_top = hill_slope = np.nan
    hill_tm_se = np.nan
    hill_ci_half = np.nan
    hill_dof = max(hill_sample_size - 4, 1)
    
    if hill_params is not None:
        hill_bottom = float(hill_params[0])
        hill_top = float(hill_params[1])
        hill_slope = float(hill_params[3])
    
    if hill_pcov is not None and np.ndim(hill_pcov) == 2 and hill_pcov.shape[0] > 2:
        var_tm = float(hill_pcov[2, 2])
        if np.isfinite(var_tm) and var_tm >= 0:
            hill_tm_se = float(np.sqrt(var_tm))
            if hill_dof > 0:
                try:
                    t_multiplier = float(t_dist.ppf(0.975, hill_dof))
                    if np.isfinite(t_multiplier):
                        hill_ci_half = hill_tm_se * t_multiplier
                except Exception:
                    pass
    
    # 选择最终 Tm
    if hill_fit_success and not np.isnan(Tm_hill):
        Tm_auc = Tm_hill
        tm_method_used = 'hill_fit'
    elif not np.isnan(Tm_hill):
        if T_interp.min() <= Tm_hill <= T_interp.max():
            Tm_auc = Tm_hill
            tm_method_used = 'hill_fit_lowconf'
        else:
            Tm_auc = Tm_midpoint
            tm_method_used = 'midpoint'
    else:
        Tm_auc = Tm_midpoint
        tm_method_used = 'midpoint'
    
    quality = _calculate_progress_quality(T_interp, p_interp)
    
    # 置信区间
    if not np.isnan(hill_ci_half):
        confidence_interval = (Tm_auc - hill_ci_half, Tm_auc + hill_ci_half)
    else:
        confidence_interval = np.nan
    
    # 状态 SNR
    state_snr = np.nan
    if hill_fit_curve is not None and np.size(hill_fit_curve) == np.size(p_interp):
        residuals = p_interp - hill_fit_curve
        noise_std = float(np.nanstd(residuals))
        signal_span = float(np.nanmax(p_interp) - np.nanmin(p_interp))
        if noise_std > 0:
            state_snr = signal_span / (noise_std * 2.0)
    
    return {
        'success': True,
        'Tm_AUC': Tm_auc,
        'Tm_midpoint': Tm_midpoint,
        'Tm_hill': Tm_hill if hill_fit_success else np.nan,
        'tm_method_used': tm_method_used,
        'hill_r2': hill_r2,
        'hill_slope': hill_slope,
        'hill_bottom': hill_bottom,
        'hill_top': hill_top,
        'hill_tm_standard_error': hill_tm_se,
        'hill_tm_ci_half': hill_ci_half,
        'total_area': 1.0,
        'area_50_percent': 0.5,
        'progress_curve': p_interp,
        'temperature_range': T_interp,
        'quality_score': quality,
        'state_snr': state_snr,
        'method': 'progress' if baseline_mode == 'exponential' else 'progress_linear',
        'standard_error': hill_tm_se if not np.isnan(hill_tm_se) else np.nan,
        'confidence_interval': confidence_interval,
        'tsb_tm': Tm_tsb,
        'tsb_r2': r2,
        'baseline_fold': F_fold,
        'baseline_unfold': F_unfold,
        'progress_raw': p,
        'T_original': T,
    }


def _apply_baseline_correction(T: np.ndarray, derivative: np.ndarray) -> np.ndarray:
    """对导数曲线应用基线校正"""
    n_points = len(T)
    edge_points = max(5, n_points // 5)
    
    T_baseline = np.concatenate([T[:edge_points], T[-edge_points:]])
    deriv_baseline = np.concatenate([derivative[:edge_points], derivative[-edge_points:]])
    
    if len(T_baseline) > 1:
        coeffs = np.polyfit(T_baseline, deriv_baseline, 1)
        baseline = np.polyval(coeffs, T)
        return derivative - baseline
    else:
        return derivative


def _interpolate_data(T: np.ndarray, signal: np.ndarray, factor: int) -> Tuple[np.ndarray, np.ndarray]:
    """将数据插值到更高分辨率"""
    f_interp = interp1d(T, signal, kind='cubic', bounds_error=False, fill_value='extrapolate')
    T_new = np.linspace(T.min(), T.max(), len(T) * factor)
    signal_new = f_interp(T_new)
    return T_new, signal_new


def _calculate_auc_quality(
    T: np.ndarray, 
    derivative: np.ndarray, 
    cumulative_area: np.ndarray, 
    total_area: float
) -> float:
    """计算导数 AUC 方法的质量分数"""
    quality_factors = []
    
    # SNR
    signal_std = np.std(derivative)
    noise_level = np.std(derivative[:len(derivative)//10])
    if noise_level > 0:
        snr = signal_std / noise_level
        quality_factors.append(min(snr / 10.0, 1.0))
    else:
        quality_factors.append(1.0)
    
    # 单调性
    area_diff = np.diff(cumulative_area)
    monotonic_fraction = np.sum(area_diff >= 0) / len(area_diff)
    quality_factors.append(monotonic_fraction)
    
    # 陡度
    if len(derivative) > 10:
        derivative_range = np.ptp(derivative)
        derivative_mean = np.mean(np.abs(derivative))
        if derivative_mean > 0:
            steepness = derivative_range / derivative_mean
            quality_factors.append(min(steepness / 5.0, 1.0))
        else:
            quality_factors.append(0.5)
    else:
        quality_factors.append(0.5)
    
    weights = [0.4, 0.3, 0.3]
    quality_score = np.average(quality_factors, weights=weights)
    
    return np.clip(quality_score, 0.0, 1.0)


def _calculate_progress_quality(T: np.ndarray, p: np.ndarray) -> float:
    """计算进度曲线方法的质量分数"""
    if len(p) < 10:
        return 0.0
    
    rng = float(np.clip(np.nanmax(p) - np.nanmin(p), 0.0, 1.0))
    dyn = rng
    
    dp = np.diff(p)
    mono = float(np.sum(dp >= -1e-6) / max(1, len(dp)))
    
    target = 0.5
    idx = int(np.argmin(np.abs(p - target)))
    win = max(2, len(p) // 50)
    lo = max(0, idx - win)
    hi = min(len(p) - 1, idx + win)
    if hi > lo:
        slope = (p[hi] - p[lo]) / max(1e-9, (T[hi] - T[lo]))
        steep = float(np.clip(slope / 0.1, 0.0, 1.0))
    else:
        steep = 0.0
    
    weights = [0.4, 0.3, 0.3]
    return float(np.clip(np.average([dyn, mono, steep], weights=weights), 0.0, 1.0))


def _fit_hill_equation_tm(T: np.ndarray, progress: np.ndarray) -> Tuple:
    """
    使用 4 参数 Hill 方程拟合确定 Tm
    
    Returns:
        (Tm, success, r2, popt, pcov, sample_size, fit_curve)
    """
    from scipy.optimize import curve_fit
    
    try:
        def hill_4pl(T, bottom, top, Tm, slope):
            return bottom + (top - bottom) / (1 + np.exp(-slope * (T - Tm)))
        
        bottom_guess = np.min(progress)
        top_guess = np.max(progress)
        Tm_guess = T[np.argmin(np.abs(progress - 0.5))]
        
        initial_guesses = [
            [bottom_guess, top_guess, Tm_guess, 0.5],
            [0, 1, Tm_guess, 0.3],
            [0, 1, Tm_guess, 0.7],
            [bottom_guess, top_guess, Tm_guess, 0.2],
        ]
        
        bounds = (
            [0, 0.5, T.min(), 0.01],
            [0.5, 1.5, T.max(), 5.0]
        )
        
        best_fit = None
        best_r2 = -np.inf
        best_popt = None
        best_pcov = None
        
        for p0_try in initial_guesses:
            try:
                popt, pcov = curve_fit(
                    hill_4pl, T, progress,
                    p0=p0_try,
                    bounds=bounds,
                    maxfev=20000,
                    method='trf'
                )
                
                progress_fit = hill_4pl(T, *popt)
                ss_res = np.sum((progress - progress_fit) ** 2)
                ss_tot = np.sum((progress - np.mean(progress)) ** 2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                if r2 > best_r2:
                    best_r2 = r2
                    best_popt = popt
                    best_pcov = pcov
                    best_fit = progress_fit
            except:
                continue
        
        if best_popt is not None:
            bottom, top, Tm, slope = best_popt
            success = T.min() <= Tm <= T.max() and best_r2 > 0.70
            return Tm, success, best_r2, best_popt, best_pcov, len(T), best_fit
        
        return np.nan, False, np.nan, None, None, len(T), None
        
    except Exception:
        return np.nan, False, np.nan, None, None, len(T), None

