#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common QC Metrics
==================
通用的质量控制指标计算函数
"""

import numpy as np
from typing import Tuple, Optional


def calculate_state_snr(
    T: np.ndarray,
    F: np.ndarray,
    popt: np.ndarray,
    F_fit: np.ndarray
) -> float:
    """
    计算Two-State Boltzmann的State SNR

    State SNR measures how well the native and denatured states are separated
    relative to the fitting noise.

    Formula:
        State SNR = |F_D(Tm) - F_N(Tm)| / σ_residual

    Where:
        F_N(Tm) = A_N·exp(α·Tm) + D_N  (native state at Tm)
        F_D(Tm) = A_D·exp(β·Tm) + D_D  (denatured state at Tm)
        σ_residual = sqrt(RSS / df)    (residual standard error)

    Args:
        T: Temperature array
        F: Observed fluorescence
        popt: Fitted parameters [A_N, α, D_N, A_D, β, D_D, Tm, k]
        F_fit: Fitted fluorescence

    Returns:
        state_snr: float, State SNR value
    """
    if len(popt) != 8:
        # Not a TSB fit, return NaN
        return float('nan')

    A_N, alpha, D_N, A_D, beta, D_D, Tm, k = popt

    # Calculate fluorescence of N and D states at Tm
    F_N = A_N * np.exp(alpha * Tm) + D_N
    F_D = A_D * np.exp(beta * Tm) + D_D

    # Calculate residual standard error
    residuals = F - F_fit
    rss = np.sum(residuals**2)
    df = len(F) - len(popt)

    if df <= 0:
        return float('nan')

    sigma_residual = np.sqrt(rss / df)

    if sigma_residual < 1e-10:
        # Perfect fit or numerical issue
        return float('inf')

    # State SNR
    state_snr = abs(F_D - F_N) / sigma_residual

    return state_snr


def calculate_delta_aic(
    T: np.ndarray,
    F: np.ndarray,
    Tm_linear: float,
    popt_tsb: np.ndarray,
    F_fit_tsb: np.ndarray
) -> Tuple[float, float]:
    """
    计算Linear模型和TSB模型之间的ΔAIC

    ΔAIC = AIC_linear - AIC_TSB

    A positive ΔAIC means TSB is preferred over the linear model.
    log₁₀(ΔAIC) is returned for easier interpretation.

    Args:
        T: Temperature array
        F: Observed fluorescence
        Tm_linear: Tm from linear interpolation (used for baseline fitting)
        popt_tsb: TSB fitted parameters
        F_fit_tsb: TSB fitted fluorescence

    Returns:
        delta_aic: float, ΔAIC value
        log_delta_aic: float, log₁₀(ΔAIC) for interpretation
    """
    n = len(F)

    # ========== Linear Model (3 parameters) ==========
    # Fit linear baselines before and after Tm
    idx_pre = T < (Tm_linear - 5)
    idx_post = T > (Tm_linear + 5)

    if np.sum(idx_pre) > 2 and np.sum(idx_post) > 2:
        # Fit pre-transition baseline
        p_pre = np.polyfit(T[idx_pre], F[idx_pre], 1)
        F_pre = np.polyval(p_pre, T)

        # Fit post-transition baseline
        p_post = np.polyfit(T[idx_post], F[idx_post], 1)
        F_post = np.polyval(p_post, T)

        # Linear model: step function at Tm
        F_linear = np.where(T < Tm_linear, F_pre, F_post)
    else:
        # Fallback: simple linear fit to all data
        p = np.polyfit(T, F, 1)
        F_linear = np.polyval(p, T)

    RSS_linear = np.sum((F - F_linear)**2)

    # ========== TSB Model (8 parameters) ==========
    RSS_tsb = np.sum((F - F_fit_tsb)**2)

    # ========== Calculate AIC ==========
    # AIC = n·ln(RSS/n) + 2·k
    # where k is the number of parameters

    # Avoid log(0) or log(negative)
    if RSS_linear <= 0 or RSS_tsb <= 0:
        return 0.0, 0.0

    AIC_linear = n * np.log(RSS_linear / n) + 2 * 3
    AIC_tsb = n * np.log(RSS_tsb / n) + 2 * 8

    delta_aic = AIC_linear - AIC_tsb

    # log₁₀(ΔAIC) for interpretation
    if delta_aic > 0:
        log_delta_aic = np.log10(delta_aic)
    else:
        # TSB is worse than linear (should rarely happen)
        log_delta_aic = 0.0

    return delta_aic, log_delta_aic


def calculate_baseline_snr(
    F: np.ndarray,
    baseline_region: int = 10
) -> float:
    """
    计算基线信噪比

    SNR_baseline = (max(F) - min(F)) / std(F[:baseline_region])

    Args:
        F: Fluorescence array
        baseline_region: Number of points at start for baseline estimation

    Returns:
        snr: float, Baseline SNR
    """
    signal = np.ptp(F)  # max - min

    if baseline_region > len(F):
        baseline_region = len(F) // 4

    noise = np.std(F[:baseline_region])

    if noise < 1e-10:
        return float('inf')

    snr = signal / noise
    return snr


def calculate_dynamic_range(
    bottom: float,
    top: float
) -> float:
    """
    计算动态范围

    Dynamic Range = (Top - Bottom) / Top × 100%

    Args:
        bottom: Bottom plateau value
        top: Top plateau value

    Returns:
        dynamic_range: float, percentage (0-100)
    """
    if top == 0:
        return 0.0

    dynamic_range = (top - bottom) / top * 100.0
    return max(0.0, dynamic_range)


def calculate_peak_snr(
    dF_dT: np.ndarray,
    peak_idx: int,
    baseline_region: int = 10
) -> float:
    """
    计算First Derivative峰的SNR

    Peak SNR = (Peak_height - Baseline_mean) / Baseline_std

    Args:
        dF_dT: First derivative array
        peak_idx: Index of peak maximum
        baseline_region: Number of points at start for baseline

    Returns:
        peak_snr: float
    """
    peak_height = dF_dT[peak_idx]

    if baseline_region > len(dF_dT):
        baseline_region = len(dF_dT) // 4

    baseline_mean = np.mean(dF_dT[:baseline_region])
    baseline_std = np.std(dF_dT[:baseline_region])

    if baseline_std < 1e-10:
        return float('inf')

    peak_snr = (peak_height - baseline_mean) / baseline_std
    return peak_snr


def calculate_peak_width(
    T: np.ndarray,
    dF_dT: np.ndarray,
    peak_idx: int
) -> Optional[float]:
    """
    计算峰宽度 (FWHM - Full Width at Half Maximum)

    Args:
        T: Temperature array
        dF_dT: First derivative array
        peak_idx: Index of peak maximum

    Returns:
        peak_width: float (°C), or None if cannot determine
    """
    peak_height = dF_dT[peak_idx]
    half_max = peak_height / 2.0

    # Find left and right edges at half maximum
    try:
        # Left edge
        left_idx = peak_idx
        while left_idx > 0 and dF_dT[left_idx] > half_max:
            left_idx -= 1

        # Right edge
        right_idx = peak_idx
        while right_idx < len(dF_dT) - 1 and dF_dT[right_idx] > half_max:
            right_idx += 1

        if left_idx >= 0 and right_idx < len(T):
            peak_width = T[right_idx] - T[left_idx]
            return peak_width
        else:
            return None

    except Exception:
        return None
