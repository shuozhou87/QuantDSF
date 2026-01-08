#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Signal Processing Utilities
=============================
信号处理工具函数

从 V1 迁移，保持核心算法不变
"""
import numpy as np
from scipy import stats
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d


def apply_edge_dampening(signal: np.ndarray, fraction: float = 0.15) -> np.ndarray:
    """
    使用余弦锥形窗口减少边缘伪影
    
    Args:
        signal: 输入信号
        fraction: 锥形区域占信号长度的比例
    
    Returns:
        边缘抑制后的信号
    """
    if len(signal) < 10:
        return signal.copy()
    
    n = len(signal)
    dampened_signal = signal.copy()
    edge_points = int(n * fraction)
    
    if edge_points == 0:
        return dampened_signal
    
    # 左边缘：余弦从 0 到 1
    left_taper = 0.5 * (1 - np.cos(np.pi * np.arange(edge_points) / edge_points))
    # 右边缘：余弦从 1 到 0
    right_taper = 0.5 * (1 + np.cos(np.pi * np.arange(edge_points) / edge_points))
    
    dampened_signal[:edge_points] *= left_taper
    dampened_signal[-edge_points:] *= right_taper
    
    return dampened_signal


def calculate_snr(signal: np.ndarray, peak_idx: int, window_size: int = 10) -> float:
    """
    计算峰值附近的信噪比
    
    Args:
        signal: 输入信号
        peak_idx: 峰值索引
        window_size: 信号测量窗口大小
    
    Returns:
        SNR 值
    """
    if len(signal) == 0 or peak_idx < 0 or peak_idx >= len(signal):
        return 0.0
    
    # 定义峰值周围的信号窗口
    start_idx = max(0, peak_idx - window_size // 2)
    end_idx = min(len(signal), peak_idx + window_size // 2 + 1)
    
    signal_window = signal[start_idx:end_idx]
    if len(signal_window) == 0:
        return 0.0
    
    # 信号强度：峰值的绝对值
    signal_strength = abs(signal[peak_idx])
    
    # 噪声估计：使用远离峰值的区域
    noise_regions = []
    
    left_start = max(0, start_idx - 3 * window_size)
    left_end = max(0, start_idx - window_size)
    if left_end > left_start and left_start < len(signal):
        left_end = min(left_end, len(signal))
        noise_regions.extend(signal[left_start:left_end])
    
    right_start = min(len(signal), end_idx + window_size)
    right_end = min(len(signal), end_idx + 3 * window_size)
    if right_end > right_start and right_start < len(signal):
        noise_regions.extend(signal[right_start:right_end])
    
    if len(noise_regions) < 5:
        exclude_start = max(0, peak_idx - window_size)
        exclude_end = min(len(signal), peak_idx + window_size)
        noise_regions = np.concatenate([
            signal[:exclude_start],
            signal[exclude_end:]
        ])
    
    if len(noise_regions) == 0:
        return float('inf') if signal_strength > 0 else 0.0
    
    noise_level = np.std(noise_regions)
    
    if noise_level == 0:
        return float('inf') if signal_strength > 0 else 0.0
    
    return signal_strength / noise_level


def smooth_signal(signal: np.ndarray, window_length: int, poly_order: int = 2) -> np.ndarray:
    """
    使用自适应平滑处理信号
    
    Args:
        signal: 输入信号
        window_length: 平滑窗口长度
        poly_order: 多项式阶数
    
    Returns:
        平滑后的信号
    """
    if len(signal) > 200:  # 高分辨率数据
        return smooth_signal_adaptive(signal, window_length, poly_order, high_resolution_mode=True)
    else:
        return smooth_signal_adaptive(signal, window_length, poly_order, high_resolution_mode=False)


def smooth_signal_adaptive(
    signal: np.ndarray, 
    base_window_length: int, 
    poly_order: int = 2, 
    high_resolution_mode: bool = False
) -> np.ndarray:
    """
    自适应多阶段平滑
    
    Args:
        signal: 输入信号
        base_window_length: 基础窗口长度
        poly_order: 多项式阶数
        high_resolution_mode: 是否为高分辨率数据模式
    
    Returns:
        自适应平滑后的信号
    """
    if len(signal) < 10:
        return signal.copy()
    
    # 计算信号特征
    signal_range = np.max(signal) - np.min(signal)
    diff_signal = np.diff(signal)
    noise_level = np.std(diff_signal)
    snr = signal_range / noise_level if noise_level > 0 else 0
    
    n_points = len(signal)
    
    if snr > 15 and n_points > 30:
        return _multi_stage_smoothing_high_snr(signal, base_window_length, poly_order)
    elif snr > 8 or high_resolution_mode:
        return _multi_stage_smoothing_enhanced(signal, base_window_length, poly_order)
    else:
        return _conservative_smoothing(signal, base_window_length, poly_order)


def _multi_stage_smoothing_high_snr(
    signal: np.ndarray, 
    base_window_length: int, 
    poly_order: int
) -> np.ndarray:
    """高信噪比数据的多阶段平滑"""
    n_points = len(signal)
    
    # 阶段 1: 轻度预平滑
    pre_window = min(11, n_points // 8)
    if pre_window % 2 == 0:
        pre_window += 1
    pre_window = max(5, pre_window)
    
    if pre_window < n_points:
        stage1 = savgol_filter(signal, pre_window, min(2, pre_window-1))
    else:
        stage1 = signal.copy()
    
    # 阶段 2: 主平滑
    main_window = min(base_window_length, n_points // 3)
    if main_window % 2 == 0:
        main_window += 1
    main_window = max(7, main_window)
    
    if main_window < n_points:
        stage2 = savgol_filter(stage1, main_window, min(poly_order, main_window-1))
    else:
        stage2 = stage1
    
    # 阶段 3: 高斯微调
    stage3 = gaussian_filter1d(stage2, sigma=0.3)
    
    return stage3


def _multi_stage_smoothing_enhanced(
    signal: np.ndarray, 
    base_window_length: int, 
    poly_order: int
) -> np.ndarray:
    """中等信噪比数据的增强多阶段平滑"""
    n_points = len(signal)
    
    pre_window = min(15, n_points // 6)
    if pre_window % 2 == 0:
        pre_window += 1
    pre_window = max(5, pre_window)
    
    if pre_window < n_points:
        stage1 = savgol_filter(signal, pre_window, min(2, pre_window-1))
    else:
        stage1 = signal.copy()
    
    main_window = min(base_window_length, n_points // 2)
    if main_window % 2 == 0:
        main_window += 1
    main_window = max(7, main_window)
    
    if main_window < n_points:
        stage2 = savgol_filter(stage1, main_window, min(poly_order, main_window-1))
    else:
        stage2 = stage1
    
    return stage2


def _conservative_smoothing(
    signal: np.ndarray, 
    base_window_length: int, 
    poly_order: int
) -> np.ndarray:
    """低信噪比数据的保守平滑"""
    window_length = min(base_window_length, len(signal) - 1)
    if window_length % 2 == 0:
        window_length += 1
    
    window_length = min(window_length, len(signal))
    poly_order = min(poly_order, window_length - 1)
    
    if window_length < 3:
        return signal.copy()
    
    try:
        return savgol_filter(signal, window_length, poly_order)
    except:
        return signal.copy()


def detect_outliers(
    signal: np.ndarray, 
    method: str = 'zscore', 
    threshold: float = 3.0
) -> np.ndarray:
    """
    检测信号中的异常值
    
    Args:
        signal: 输入信号
        method: 检测方法 ('zscore', 'iqr')
        threshold: 异常值阈值
    
    Returns:
        布尔数组，标记异常值位置
    """
    if len(signal) == 0:
        return np.array([])
    
    if method == 'zscore':
        z_scores = np.abs(stats.zscore(signal))
        return z_scores > threshold
    
    elif method == 'iqr':
        Q1 = np.percentile(signal, 25)
        Q3 = np.percentile(signal, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        return (signal < lower_bound) | (signal > upper_bound)
    
    else:
        raise ValueError(f"未知的异常值检测方法: {method}")


def interpolate_signal(
    T: np.ndarray, 
    signal: np.ndarray, 
    method: str = 'linear', 
    num_points: int = None
) -> tuple:
    """
    将信号插值到更高分辨率
    
    Args:
        T: 温度数组
        signal: 信号数组
        method: 插值方法 ('linear', 'cubic')
        num_points: 插值后的点数
    
    Returns:
        (T_interp, signal_interp) 元组
    """
    from scipy.interpolate import interp1d
    
    if len(T) != len(signal) or len(T) < 2:
        return T.copy(), signal.copy()
    
    if num_points is None:
        num_points = len(T) * 3
    
    try:
        f_interp = interp1d(T, signal, kind=method, bounds_error=False, fill_value='extrapolate')
        T_interp = np.linspace(T.min(), T.max(), num_points)
        signal_interp = f_interp(T_interp)
        return T_interp, signal_interp
    except:
        return T.copy(), signal.copy()



