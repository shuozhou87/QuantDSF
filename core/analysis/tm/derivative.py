#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
First Derivative Method
========================
一阶导数峰值法 Tm 计算

流程:
1. 对荧光信号进行 Savitzky-Golay 平滑
2. 计算一阶导数 dF/dT
3. 检测导数峰值位置
4. 峰值温度即为 Tm
"""

import numpy as np
from scipy.signal import savgol_filter, find_peaks
from scipy.ndimage import gaussian_filter1d
from typing import Tuple, List, Optional

from ...models import RawData, TmResult, AnalysisConfig, AnalysisMethod


def smooth_signal(
    F: np.ndarray,
    window_length: int = 21,
    poly_order: int = 2
) -> np.ndarray:
    """
    使用 Savitzky-Golay 滤波器平滑信号
    
    Args:
        F: 荧光数组
        window_length: 窗口长度（奇数）
        poly_order: 多项式阶数
    
    Returns:
        平滑后的信号
    """
    # 确保窗口长度为奇数且不超过数据长度
    if window_length % 2 == 0:
        window_length += 1
    window_length = min(window_length, len(F) - 1)
    if window_length < poly_order + 2:
        window_length = poly_order + 2
        if window_length % 2 == 0:
            window_length += 1
    
    return savgol_filter(F, window_length, poly_order)


def compute_derivative(
    T: np.ndarray,
    F: np.ndarray,
    smooth: bool = True,
    window_length: int = 21,
    poly_order: int = 2,
    use_tsb_smoothing: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    计算一阶导数 dF/dT

    Args:
        T: 温度数组
        F: 荧光数组
        smooth: 是否先平滑
        window_length: 平滑窗口长度
        poly_order: 多项式阶数
        use_tsb_smoothing: 是否使用TSB模型进行平滑(推荐)

    Returns:
        Tuple of (温度数组, 导数数组)
    """
    if smooth and use_tsb_smoothing:
        # 策略: 使用TSB模型拟合数据,然后使用解析导数
        # 优势: 物理意义明确,去噪效果好,导数完全平滑(无数值误差)
        try:
            from .boltzmann import fit_boltzmann_model, boltzmann_exp_derivative

            # DEBUG: 记录TSB拟合尝试
            with open('tsb_smoothing_debug.log', 'a') as f:
                f.write(f"\n=== TSB SMOOTHING ATTEMPT ===\n")
                f.write(f"use_tsb_smoothing={use_tsb_smoothing}, smooth={smooth}\n")

            # 尝试TSB拟合
            result = fit_boltzmann_model(T, F, model='exponential')

            # DEBUG: 记录拟合结果
            with open('tsb_smoothing_debug.log', 'a') as f:
                if result:
                    f.write(f"TSB fit result: success={result.get('success')}, R^2={result.get('R_squared', 0):.4f}\n")
                else:
                    f.write(f"TSB fit result: None\n")

            if result and result.get('success') and result.get('R_squared', 0) > 0.85:
                # 拟合成功,使用TSB模型的解析导数
                params = result.get('parameters', {})

                # DEBUG: 记录使用TSB导数
                with open('tsb_smoothing_debug.log', 'a') as f:
                    f.write(f"[SUCCESS] Using TSB analytical derivative (R^2={result.get('R_squared', 0):.4f})\n")

                # 提取参数
                A_N = params.get('A_N', 0)
                alpha = params.get('alpha', 0)
                D_N = params.get('D_N', 0)
                A_D = params.get('A_D', 0)
                beta = params.get('beta', 0)
                D_D = params.get('D_D', 0)
                Tm = params.get('Tm', 0)
                k = params.get('k', 0)

                # 使用解析导数(完全平滑,无数值误差)
                derivative = boltzmann_exp_derivative(
                    T, A_N, alpha, D_N, A_D, beta, D_D, Tm, k
                )

                return T, derivative
            else:
                # TSB拟合失败,回退到传统方法
                with open('tsb_smoothing_debug.log', 'a') as f:
                    f.write(f"[FAILED] Falling back to SG filter (R^2 threshold not met)\n")
                pass
        except Exception as e:
            # 如果TSB拟合出错,回退到传统方法
            with open('tsb_smoothing_debug.log', 'a') as f:
                f.write(f"[EXCEPTION] TSB smoothing exception: {e}\n")
            pass

    # 传统平滑方法 (回退或use_tsb_smoothing=False时)
    if smooth:
        F_smooth = smooth_signal(F, window_length, poly_order)
    else:
        F_smooth = F

    # 计算导数
    dT = np.gradient(T)
    dF = np.gradient(F_smooth)
    derivative = dF / dT

    return T, derivative


def find_derivative_peaks(
    T: np.ndarray,
    derivative: np.ndarray,
    method: str = "find_peaks",
    temp_range: tuple = None
) -> List[Tuple[float, float]]:
    """
    检测导数峰值

    Args:
        T: 温度数组
        derivative: 导数数组
        method: 检测方法 (find_peaks/polynomial_fit/gaussian_deconvolution)
        temp_range: optional (min, max) for deconvolution fitting region

    Returns:
        List of (peak_temperature, peak_height) tuples
    """
    if method == "gaussian_deconvolution":
        # Dual-peak Gaussian deconvolution
        from .gaussian_deconv import deconvolute_dual_peaks
        deconv = deconvolute_dual_peaks(T, derivative, temp_range=temp_range)
        if deconv['success'] and len(deconv['peaks']) >= 2:
            # Return both peaks as (Tm, peak_height) tuples, sorted by temperature
            return [(p['tm'], p['amplitude']) for p in deconv['peaks']]
        # Fallback: if deconvolution fails, fall through to single-peak find_peaks
        pass

    if method == "find_peaks" or method == "gaussian_deconvolution":
        # Single-peak: find |dF/dT| absolute maximum
        abs_derivative = np.abs(derivative)
        peak_idx = np.argmax(abs_derivative)
        Tm_simple = T[peak_idx]
        peak_height = derivative[peak_idx]

        # Parabolic refinement for sub-sample precision
        half_width = 3
        start = max(0, peak_idx - half_width)
        end = min(len(T), peak_idx + half_width + 1)

        if end - start >= 3:
            T_local = T[start:end]
            deriv_local = derivative[start:end]

            try:
                coeffs = np.polyfit(T_local, deriv_local, 2)
                if coeffs[0] != 0:
                    Tm_refined = -coeffs[1] / (2 * coeffs[0])
                    if T_local[0] <= Tm_refined <= T_local[-1]:
                        peak_height_refined = np.polyval(coeffs, Tm_refined)
                        return [(Tm_refined, peak_height_refined)]
            except:
                pass

        return [(Tm_simple, peak_height)]

    elif method == "polynomial_fit":
        # 在最小值附近进行多项式拟合精细化
        peak_idx = np.argmin(derivative)
        
        # 取周围 5 个点进行二次多项式拟合
        half_width = 5
        start = max(0, peak_idx - half_width)
        end = min(len(T), peak_idx + half_width + 1)
        
        T_local = T[start:end]
        deriv_local = derivative[start:end]
        
        if len(T_local) >= 3:
            coeffs = np.polyfit(T_local, deriv_local, 2)
            # 二次多项式极值点
            Tm_refined = -coeffs[1] / (2 * coeffs[0])
            peak_height = np.polyval(coeffs, Tm_refined)
            return [(Tm_refined, peak_height)]
        else:
            return [(T[peak_idx], derivative[peak_idx])]
    
    else:
        # 默认使用简单的最小值检测
        peak_idx = np.argmin(derivative)
        return [(T[peak_idx], derivative[peak_idx])]


def calculate_tm_derivative(
    data: RawData,
    config: AnalysisConfig
) -> TmResult:
    """
    使用导数方法计算 Tm
    
    Args:
        data: 原始数据
        config: 分析配置
    
    Returns:
        TmResult: 分析结果
    """
    T = data.T
    F = data.F
    
    warnings = []
    quality_flag = "✓"
    
    try:
        # Step 1: 计算导数
        T_deriv, derivative = compute_derivative(
            T, F,
            smooth=True,
            window_length=config.window_length,
            poly_order=config.sg_poly_order
        )
        
        # Step 2: 检测峰值
        peaks = find_derivative_peaks(
            T_deriv, derivative,
            method=config.derivative_peak_method
        )
        
        if not peaks:
            return TmResult(
                tm=float('nan'),
                r_squared=0.0,
                method=AnalysisMethod.DERIVATIVE,
                quality_flag="❌",
                warnings=["未检测到导数峰"]
            )

        # For Gaussian deconvolution, also run full deconvolution for metadata
        additional_peaks = None
        deconv_r2 = None
        deconv_baseline = None

        if config.derivative_peak_method == "gaussian_deconvolution" and len(peaks) >= 2:
            from .gaussian_deconv import deconvolute_dual_peaks
            deconv = deconvolute_dual_peaks(T_deriv, derivative)
            if deconv['success']:
                additional_peaks = deconv['peaks']  # list of dicts with tm, amplitude, width, area
                deconv_r2 = deconv['fit_r_squared']
                deconv_baseline = deconv['baseline']

        # Primary Tm = most prominent peak (largest absolute amplitude)
        primary_idx = 0
        if len(peaks) > 1:
            primary_idx = max(range(len(peaks)), key=lambda i: abs(peaks[i][1]))

        Tm, peak_height = peaks[primary_idx]

        # Step 3: Quality assessment
        noise_level = np.std(derivative[:10])  # estimate noise from first 10 points
        snr = abs(peak_height) / noise_level if noise_level > 0 else 0

        r2_proxy = min(1.0, snr / 10.0)

        if snr < 3:
            warnings.append(f"信噪比较低 (SNR={snr:.1f})")
            quality_flag = "⚠️"

        if Tm < T.min() + 5 or Tm > T.max() - 5:
            warnings.append("Tm 接近温度范围边界")
            quality_flag = "⚠️"

        if len(peaks) >= 2:
            warnings.append(f"Dual peaks detected: {peaks[0][0]:.1f}°C and {peaks[1][0]:.1f}°C")

        # Estimate peak width
        half_max = peak_height / 2
        above_half = np.where(derivative < half_max)[0]
        if len(above_half) >= 2:
            peak_width = T[above_half[-1]] - T[above_half[0]]
        else:
            peak_width = None

        return TmResult(
            tm=float(Tm),
            r_squared=float(r2_proxy),
            method=AnalysisMethod.DERIVATIVE,
            peak_height=float(peak_height),
            peak_width=float(peak_width) if peak_width else None,
            snr=float(snr),
            quality_flag=quality_flag,
            warnings=warnings,
            additional_peaks=additional_peaks,
            deconv_r_squared=deconv_r2,
            deconv_baseline=deconv_baseline
        )
        
    except Exception as e:
        return TmResult(
            tm=float('nan'),
            r_squared=0.0,
            method=AnalysisMethod.DERIVATIVE,
            quality_flag="❌",
            warnings=[f"导数分析失败: {e}"]
        )


