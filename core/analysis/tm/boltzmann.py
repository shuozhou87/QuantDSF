#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Two-State Boltzmann Fitting
=============================
两态 Boltzmann 拟合模块

从 V1 迁移，保持核心算法不变
"""
import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, Optional, Tuple, Any


def boltzmann_exp(
    T: np.ndarray,
    A_N: float, alpha: float, D_N: float,
    A_D: float, beta: float, D_D: float,
    Tm: float, k: float
) -> np.ndarray:
    """
    带指数基线的两态 Boltzmann 转变模型

    F(T) = (1-f_D) * F_N(T) + f_D * F_D(T)

    其中:
    - F_N(T) = A_N * exp(α*T) + D_N (天然态基线)
    - F_D(T) = A_D * exp(β*T) + D_D (变性态基线)
    - f_D = 1 / (1 + exp(-k*(T-Tm))) (变性比例)

    Args:
        T: 温度数组
        A_N, alpha, D_N: 天然态基线参数
        A_D, beta, D_D: 变性态基线参数
        Tm: 熔解温度
        k: 转变陡度参数

    Returns:
        计算的荧光值
    """
    F_N = A_N * np.exp(alpha * T) + D_N
    F_D = A_D * np.exp(beta * T) + D_D

    delta_T = T - Tm
    exp_term = np.exp(-k * delta_T)
    exp_term = np.clip(exp_term, 1e-10, 1e10)

    f_D = 1 / (1 + exp_term)
    F_total = (1 - f_D) * F_N + f_D * F_D

    return F_total


def boltzmann_exp_derivative(
    T: np.ndarray,
    A_N: float, alpha: float, D_N: float,
    A_D: float, beta: float, D_D: float,
    Tm: float, k: float
) -> np.ndarray:
    """
    Boltzmann模型的解析一阶导数 dF/dT

    推导:
    F(T) = (1-f_D)*F_N + f_D*F_D
    dF/dT = (1-f_D)*dF_N/dT + f_D*dF_D/dT + df_D/dT*(F_D - F_N)

    其中:
    - dF_N/dT = A_N * α * exp(α*T)
    - dF_D/dT = A_D * β * exp(β*T)
    - df_D/dT = k * f_D * (1 - f_D)

    Args:
        T: 温度数组
        参数同boltzmann_exp

    Returns:
        导数值数组 dF/dT
    """
    # 计算基线和导数
    F_N = A_N * np.exp(alpha * T) + D_N
    F_D = A_D * np.exp(beta * T) + D_D
    dF_N_dT = A_N * alpha * np.exp(alpha * T)
    dF_D_dT = A_D * beta * np.exp(beta * T)

    # 计算变性比例
    delta_T = T - Tm
    exp_term = np.exp(-k * delta_T)
    exp_term = np.clip(exp_term, 1e-10, 1e10)
    f_D = 1 / (1 + exp_term)

    # df_D/dT = k * f_D * (1 - f_D)
    df_D_dT = k * f_D * (1 - f_D)

    # 总导数
    derivative = (1 - f_D) * dF_N_dT + f_D * dF_D_dT + df_D_dT * (F_D - F_N)

    return derivative


def boltzmann_linear(
    T: np.ndarray,
    A_N: float, B_N: float,
    A_D: float, B_D: float,
    Tm: float, k: float
) -> np.ndarray:
    """
    带线性基线的两态 Boltzmann 转变模型
    
    Args:
        T: 温度数组
        A_N, B_N: 天然态线性基线参数 (斜率, 截距)
        A_D, B_D: 变性态线性基线参数
        Tm: 熔解温度
        k: 转变陡度参数
    
    Returns:
        计算的荧光值
    """
    F_N = A_N * T + B_N
    F_D = A_D * T + B_D
    
    delta_T = T - Tm
    exp_term = np.exp(-k * delta_T)
    exp_term = np.clip(exp_term, 1e-10, 1e10)
    
    f_D = 1 / (1 + exp_term)
    F_total = (1 - f_D) * F_N + f_D * F_D
    
    return F_total


def fit_boltzmann_model(
    T: np.ndarray,
    F: np.ndarray,
    model: str = 'exponential',
    initial_guess: Optional[list] = None,
    bounds: Optional[Tuple] = None,
    prefer_linear: bool = False
) -> Optional[Dict[str, Any]]:
    """
    拟合两态 Boltzmann 模型
    
    Args:
        T: 温度数组
        F: 荧光数组
        model: 基线模型类型 ('exponential' 或 'linear')
        initial_guess: 初始参数猜测
        bounds: 参数边界
    
    Returns:
        拟合结果字典，包含 Tm、R²、参数等
    """
    if len(T) != len(F) or len(T) < 8:
        return None
    
    # 移除无效值
    valid_mask = np.logical_and(np.isfinite(T), np.isfinite(F))
    T_clean = T[valid_mask]
    F_clean = F[valid_mask]
    
    if len(T_clean) < 8:
        return None
    
    try:
        if model == 'exponential':
            # 先跑线性，作为指数的稳健初猜；若指数失败则回退线性，再失败才 None
            lin_res = None
            if prefer_linear:
                lin_res = _fit_linear_model(T_clean, F_clean, initial_guess, bounds=None)
            ig_from_lin = _linear_to_exp_guess(T_clean, lin_res) if lin_res and lin_res.get("success") else None
            exp_res = _fit_exponential_model(T_clean, F_clean, ig_from_lin or initial_guess, bounds)
            if exp_res and exp_res.get("success"):
                return exp_res
            if lin_res and lin_res.get("success"):
                return lin_res
            return exp_res or lin_res
        elif model == 'linear':
            return _fit_linear_model(T_clean, F_clean, initial_guess, bounds)
        else:
            raise ValueError(f"未知模型类型: {model}")
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'Tm': np.nan,
            'R_squared': 0.0,
            'parameters': {},
            'fitted_curve': np.full_like(F, np.nan)
        }


def _fit_exponential_model(
    T: np.ndarray,
    F: np.ndarray,
    initial_guess: Optional[list],
    bounds: Optional[Tuple]
) -> Dict[str, Any]:
    """拟合指数基线 Boltzmann 模型"""

    # 使用V1的成功策略：无边界约束或非常宽松的边界
    # V1不使用bounds，让优化器有更大自由度
    if bounds is None:
        # 使用非常宽松的边界，主要防止数值溢出
        F_min, F_max = F.min(), F.max()
        F_range = F_max - F_min
        T_min, T_max = T.min(), T.max()

        # 极宽松的边界（比原来宽10倍）
        lower_bounds = [
            -F_range * 10, -1.0, F_min - F_range * 10,
            -F_range * 10, -1.0, F_min - F_range * 10,
            T_min - 50, 0.001
        ]
        upper_bounds = [
            F_range * 10, 1.0, F_max + F_range * 10,
            F_range * 10, 1.0, F_max + F_range * 10,
            T_max + 50, 10.0
        ]
        bounds = (lower_bounds, upper_bounds)

    # 使用V1的初始参数策略
    F_center = (F.max() + F.min()) / 2
    T_center = (T.max() + T.min()) / 2

    initial_guesses = []
    if initial_guess is not None:
        initial_guesses.append(initial_guess)

    # V1的3组初猜（已验证有效，R²=0.998）
    initial_guesses.extend([
        [F.max(), 0.005, F.min(), F.max()*0.8, 0.005, F.min()*1.2, T_center, 0.3],
        [F.max(), 0.01, F.min(), F.max()*0.9, 0.01, F.min()*1.1, T_center, 0.4],
        [F.max(), 0.003, F.min(), F.max()*0.7, 0.003, F.min()*1.3, T_center, 0.2],
    ])
    
    best_rss = float('inf')
    best_popt = None
    best_pcov = None
    last_error = None
    
    for p0_try in initial_guesses:
        try:
            popt, pcov = curve_fit(
                boltzmann_exp, T, F,
                p0=p0_try,
                bounds=bounds,
                maxfev=200000
            )
            
            F_fitted = boltzmann_exp(T, *popt)
            rss = np.sum((F - F_fitted)**2)
            
            if rss < best_rss:
                best_rss = rss
                best_popt = popt
                best_pcov = pcov
                
        except Exception as e:
            last_error = e
            continue
    
    if best_popt is None:
        if last_error:
            raise last_error
        else:
            raise RuntimeError("所有初始猜测都无法收敛")
    
    popt = best_popt
    pcov = best_pcov
    
    A_N, alpha, D_N, A_D, beta, D_D, Tm, k = popt
    
    F_fitted = boltzmann_exp(T, *popt)
    r_squared = _calculate_r_squared(F, F_fitted)
    
    # 计算状态 SNR
    residuals = F - F_fitted
    rss = np.sum(residuals**2)
    degrees_freedom = len(T) - len(popt)
    sigma_resid = np.sqrt(rss / degrees_freedom) if degrees_freedom > 0 else np.nan

    F_N_at_Tm = A_N * np.exp(alpha * Tm) + D_N
    F_D_at_Tm = A_D * np.exp(beta * Tm) + D_D
    deltaF = abs(F_D_at_Tm - F_N_at_Tm)
    state_snr = deltaF / sigma_resid if sigma_resid > 0 else np.nan

    # 计算 ΔAIC (AIC_linear - AIC_TSB)
    # Linear model: 3-parameter (pre-slope, post-slope, Tm)
    n = len(T)
    idx_pre = T < (Tm - 5)
    idx_post = T > (Tm + 5)

    if np.sum(idx_pre) > 2 and np.sum(idx_post) > 2:
        # Fit linear baselines before and after Tm
        p_pre = np.polyfit(T[idx_pre], F[idx_pre], 1)
        F_pre = np.polyval(p_pre, T)

        p_post = np.polyfit(T[idx_post], F[idx_post], 1)
        F_post = np.polyval(p_post, T)

        # Linear model: step function at Tm
        F_linear = np.where(T < Tm, F_pre, F_post)
        RSS_linear = np.sum((F - F_linear)**2)
    else:
        # Fallback: simple linear fit
        p = np.polyfit(T, F, 1)
        F_linear = np.polyval(p, T)
        RSS_linear = np.sum((F - F_linear)**2)

    # Calculate AIC
    RSS_tsb = rss
    if RSS_linear > 0 and RSS_tsb > 0:
        AIC_linear = n * np.log(RSS_linear / n) + 2 * 3
        AIC_tsb = n * np.log(RSS_tsb / n) + 2 * 8
        delta_aic = AIC_linear - AIC_tsb
        log_delta_aic = np.log10(delta_aic) if delta_aic > 0 else 0.0
    else:
        delta_aic = 0.0
        log_delta_aic = 0.0

    param_std = np.sqrt(np.diag(pcov))

    return {
        'success': True,
        'Tm': Tm,
        'Tm_std': param_std[6],
        'R_squared': r_squared,
        'state_snr': state_snr,
        'delta_aic': delta_aic,
        'log_delta_aic': log_delta_aic,
        'steepness': k,
        'steepness_std': param_std[7],
        'parameters': {
            'A_N': A_N, 'alpha': alpha, 'D_N': D_N,
            'A_D': A_D, 'beta': beta, 'D_D': D_D,
            'Tm': Tm, 'k': k
        },
        'parameter_std': {
            'A_N': param_std[0], 'alpha': param_std[1], 'D_N': param_std[2],
            'A_D': param_std[3], 'beta': param_std[4], 'D_D': param_std[5],
            'Tm': param_std[6], 'k': param_std[7]
        },
        'fitted_curve': F_fitted,
        'covariance_matrix': pcov
    }


def _fit_linear_model(
    T: np.ndarray,
    F: np.ndarray,
    initial_guess: Optional[list],
    bounds: Optional[Tuple]
) -> Dict[str, Any]:
    """拟合线性基线 Boltzmann 模型"""

    if initial_guess is None:
        initial_guess = _generate_linear_initial_guess(T, F)

    if bounds is None:
        bounds = _generate_linear_bounds(T, F)

    try:
        popt, pcov = curve_fit(
            boltzmann_linear, T, F,
            p0=initial_guess,
            bounds=bounds,
            maxfev=5000
        )
    except Exception as e:
        # 线性拟合失败，返回失败结果
        return {
            'success': False,
            'error': str(e),
            'Tm': np.nan,
            'R_squared': 0.0,
            'parameters': {},
            'fitted_curve': np.full_like(F, np.nan)
        }
    
    A_N, B_N, A_D, B_D, Tm, k = popt
    
    F_fitted = boltzmann_linear(T, *popt)
    r_squared = _calculate_r_squared(F, F_fitted)
    
    residuals = F - F_fitted
    rss = np.sum(residuals**2)
    degrees_freedom = len(T) - len(popt)
    sigma_resid = np.sqrt(rss / degrees_freedom) if degrees_freedom > 0 else np.nan
    
    F_N_at_Tm = A_N * Tm + B_N
    F_D_at_Tm = A_D * Tm + B_D
    deltaF = abs(F_D_at_Tm - F_N_at_Tm)
    state_snr = deltaF / sigma_resid if sigma_resid > 0 else np.nan
    
    param_std = np.sqrt(np.diag(pcov))
    
    return {
        'success': True,
        'Tm': Tm,
        'Tm_std': param_std[4],
        'R_squared': r_squared,
        'state_snr': state_snr,
        'steepness': k,
        'steepness_std': param_std[5],
        'parameters': {
            'A_N': A_N, 'B_N': B_N,
            'A_D': A_D, 'B_D': B_D,
            'Tm': Tm, 'k': k
        },
        'parameter_std': {
            'A_N': param_std[0], 'B_N': param_std[1],
            'A_D': param_std[2], 'B_D': param_std[3],
            'Tm': param_std[4], 'k': param_std[5]
        },
        'fitted_curve': F_fitted,
        'covariance_matrix': pcov
    }


def _generate_exp_initial_guess(T: np.ndarray, F: np.ndarray) -> list:
    """生成指数模型的初始参数猜测"""
    T_min, T_max = T.min(), T.max()
    F_min, F_max = F.min(), F.max()
    
    F_mid = (F_min + F_max) / 2
    Tm_idx = np.argmin(np.abs(F - F_mid))
    Tm_guess = T[Tm_idx]
    
    k_guess = 0.1
    
    n_points = max(5, len(T) // 5)
    F_native = F[:n_points]
    F_denat = F[-n_points:]
    
    A_N_guess = 0.0
    alpha_guess = 0.001
    D_N_guess = np.mean(F_native)
    
    A_D_guess = 0.0
    beta_guess = 0.001  
    D_D_guess = np.mean(F_denat)
    
    return [A_N_guess, alpha_guess, D_N_guess, A_D_guess, beta_guess, D_D_guess, Tm_guess, k_guess]


def _generate_linear_initial_guess(T: np.ndarray, F: np.ndarray) -> list:
    """生成线性模型的初始参数猜测"""
    F_min, F_max = F.min(), F.max()
    
    F_mid = (F_min + F_max) / 2
    Tm_idx = np.argmin(np.abs(F - F_mid))
    Tm_guess = T[Tm_idx]
    
    k_guess = 0.1
    
    n_points = max(5, len(T) // 5)
    
    T_native = T[:n_points]
    F_native = F[:n_points]
    if len(T_native) > 1:
        A_N_guess = (F_native[-1] - F_native[0]) / (T_native[-1] - T_native[0])
        B_N_guess = F_native[0] - A_N_guess * T_native[0]
    else:
        A_N_guess = 0.0
        B_N_guess = F_native[0]
    
    T_denat = T[-n_points:]
    F_denat = F[-n_points:]
    if len(T_denat) > 1:
        A_D_guess = (F_denat[-1] - F_denat[0]) / (T_denat[-1] - T_denat[0])
        B_D_guess = F_denat[0] - A_D_guess * T_denat[0]
    else:
        A_D_guess = 0.0
        B_D_guess = F_denat[0]
    
    return [A_N_guess, B_N_guess, A_D_guess, B_D_guess, Tm_guess, k_guess]


def _generate_exp_bounds(T: np.ndarray, F: np.ndarray) -> Tuple:
    """生成指数模型的参数边界"""
    T_min, T_max = T.min(), T.max()
    F_min, F_max = F.min(), F.max()
    F_range = F_max - F_min
    
    lower_bounds = [
        -F_range, -0.1, F_min - F_range,
        -F_range, -0.1, F_min - F_range,
        T_min - 10, 0.01
    ]
    
    upper_bounds = [
        F_range, 0.1, F_max + F_range,
        F_range, 0.1, F_max + F_range,
        T_max + 10, 1.0
    ]
    
    return (lower_bounds, upper_bounds)


def _linear_to_exp_guess(T: np.ndarray, linear_result: Dict[str, Any]) -> list:
    """
    将线性拟合结果转换为指数模型的初始猜测（保守映射）。
    确保生成的初猜在指数模型的边界范围内。
    """
    params = linear_result.get("parameters", {})
    A_N_lin = params.get("A_N", 0.0)
    B_N_lin = params.get("B_N", 0.0)
    A_D_lin = params.get("A_D", 0.0)
    B_D_lin = params.get("B_D", 0.0)
    Tm_lin = params.get("Tm", float(np.median(T)))
    k_lin = params.get("k", 0.2)

    # 获取温度和荧光范围（用于边界检查）
    T_min, T_max = T.min(), T.max()

    # 从linear_result中获取荧光数据来计算范围
    fitted_curve = linear_result.get('fitted_curve')
    if fitted_curve is not None and len(fitted_curve) > 0:
        F_min, F_max = fitted_curve.min(), fitted_curve.max()
    else:
        # 回退：使用Tm处的基线估计
        F_N_at_Tm = A_N_lin * Tm_lin + B_N_lin
        F_D_at_Tm = A_D_lin * Tm_lin + B_D_lin
        F_min = min(F_N_at_Tm, F_D_at_Tm) * 0.9
        F_max = max(F_N_at_Tm, F_D_at_Tm) * 1.1

    F_range = F_max - F_min

    # 将线性截距映射为指数偏移，将斜率映射为微弱的 alpha/beta
    A_N = 0.0
    alpha = np.clip(A_N_lin / max(abs(B_N_lin) + 1e-6, 1.0) * 0.01, -0.05, 0.05)
    # 确保D_N在边界内 [F_min - F_range, F_max + F_range]
    D_N = np.clip(B_N_lin, F_min - F_range, F_max + F_range)

    A_D = 0.0
    beta = np.clip(A_D_lin / max(abs(B_D_lin) + 1e-6, 1.0) * 0.01, -0.05, 0.05)
    # 确保D_D在边界内
    D_D = np.clip(B_D_lin, F_min - F_range, F_max + F_range)

    Tm_guess = float(np.clip(Tm_lin, T_min, T_max))
    k_guess = float(np.clip(k_lin, 0.05, 1.0))

    return [A_N, alpha, D_N, A_D, beta, D_D, Tm_guess, k_guess]


def _generate_linear_bounds(T: np.ndarray, F: np.ndarray) -> Tuple:
    """生成线性模型的参数边界"""
    T_min, T_max = T.min(), T.max()
    F_min, F_max = F.min(), F.max()
    F_range = F_max - F_min
    T_range = T_max - T_min
    
    max_slope = F_range / T_range * 2
    
    lower_bounds = [
        -max_slope, F_min - F_range,
        -max_slope, F_min - F_range,
        T_min - 10, 0.01
    ]
    
    upper_bounds = [
        max_slope, F_max + F_range,
        max_slope, F_max + F_range,
        T_max + 10, 1.0
    ]
    
    return (lower_bounds, upper_bounds)


def _calculate_r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """计算 R² (决定系数)"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    
    if ss_tot == 0:
        return 1.0 if ss_res < 1e-10 else 0.0
    
    return 1 - (ss_res / ss_tot)

