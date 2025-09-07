#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal processing utilities for nanoDSF analysis
"""
import numpy as np
from scipy import stats


def apply_edge_dampening(signal, fraction=0.15):
    """
    Apply edge dampening using cosine taper to reduce artifacts
    at the beginning and end of the signal
    
    Parameters:
        signal (np.ndarray): Input signal
        fraction (float): Fraction of signal length to apply tapering (default 0.15)
    
    Returns:
        np.ndarray: Edge-dampened signal
    """
    if len(signal) < 10:  # Not enough data points
        return signal.copy()
    
    n = len(signal)
    dampened_signal = signal.copy()
    
    # Calculate the number of points to dampen at each edge
    edge_points = int(n * fraction)
    
    if edge_points == 0:
        return dampened_signal
    
    # Create cosine taper window
    # Left edge: cosine taper from 0 to 1
    left_taper = 0.5 * (1 - np.cos(np.pi * np.arange(edge_points) / edge_points))
    
    # Right edge: cosine taper from 1 to 0
    right_taper = 0.5 * (1 + np.cos(np.pi * np.arange(edge_points) / edge_points))
    
    # Apply tapering
    dampened_signal[:edge_points] *= left_taper
    dampened_signal[-edge_points:] *= right_taper
    
    return dampened_signal


def calculate_snr(signal, peak_idx, window_size=10):
    """
    Calculate Signal-to-Noise Ratio around a peak
    
    Parameters:
        signal (np.ndarray): Input signal
        peak_idx (int): Index of the peak
        window_size (int): Size of window around peak for signal measurement
    
    Returns:
        float: SNR value
    """
    if len(signal) == 0 or peak_idx < 0 or peak_idx >= len(signal):
        return 0.0
    
    # Define signal window around the peak
    start_idx = max(0, peak_idx - window_size // 2)
    end_idx = min(len(signal), peak_idx + window_size // 2 + 1)
    
    signal_window = signal[start_idx:end_idx]
    
    if len(signal_window) == 0:
        return 0.0
    
    # Signal strength: use absolute value of peak
    signal_strength = abs(signal[peak_idx])
    
    # Noise estimation: use areas far from the peak
    noise_regions = []
    
    # Left noise region
    left_start = max(0, start_idx - 3 * window_size)
    left_end = max(0, start_idx - window_size)
    if left_end > left_start and left_start < len(signal):
        left_end = min(left_end, len(signal))
        noise_regions.extend(signal[left_start:left_end])
    
    # Right noise region  
    right_start = min(len(signal), end_idx + window_size)
    right_end = min(len(signal), end_idx + 3 * window_size)
    if right_end > right_start and right_start < len(signal):
        noise_regions.extend(signal[right_start:right_end])
    
    # If we don't have enough noise data, use the entire signal excluding the peak region
    if len(noise_regions) < 5:
        exclude_start = max(0, peak_idx - window_size)
        exclude_end = min(len(signal), peak_idx + window_size)
        noise_regions = np.concatenate([
            signal[:exclude_start],
            signal[exclude_end:]
        ])
    
    if len(noise_regions) == 0:
        return float('inf') if signal_strength > 0 else 0.0
    
    # Calculate noise as standard deviation
    noise_level = np.std(noise_regions)
    
    # Avoid division by zero
    if noise_level == 0:
        return float('inf') if signal_strength > 0 else 0.0
    
    snr = signal_strength / noise_level
    return snr


def smooth_signal_adaptive(signal, base_window_length, poly_order=2, high_resolution_mode=False):
    """
    Adaptive smoothing for high-resolution data with noise assessment
    
    Parameters:
        signal (np.ndarray): Input signal
        base_window_length (int): Base window length for smoothing
        poly_order (int): Polynomial order for Savitzky-Golay filter
        high_resolution_mode (bool): If True, applies additional pre-smoothing for very noisy data
    
    Returns:
        np.ndarray: Adaptively smoothed signal
    """
    from scipy.signal import savgol_filter
    
    if len(signal) < 10:
        return signal.copy()
    
    # Ensure window_length is odd and valid
    window_length = base_window_length
    if window_length % 2 == 0:
        window_length += 1
    
    # For high-resolution data, assess noise level first
    if high_resolution_mode and len(signal) > 50:
        # Calculate noise level using high-frequency components
        diff_signal = np.diff(signal)
        noise_level = np.std(diff_signal)
        signal_range = np.max(signal) - np.min(signal)
        
        # If noise is significant relative to signal range, apply multi-stage smoothing
        noise_ratio = noise_level / signal_range if signal_range > 0 else 0
        
        if noise_ratio > 0.05:  # High noise detected
            # Stage 1: Light pre-smoothing with smaller window
            pre_window = min(base_window_length // 2 + 1, 15)
            if pre_window % 2 == 0:
                pre_window += 1
            if pre_window >= 5 and pre_window < len(signal):
                pre_smoothed = savgol_filter(signal, pre_window, min(poly_order, pre_window-1))
            else:
                pre_smoothed = signal.copy()
            
            # Stage 2: Main smoothing with larger window on pre-smoothed data
            main_window = min(window_length * 2, len(signal) - 1)
            if main_window % 2 == 0:
                main_window -= 1
            if main_window >= 5:
                final_signal = savgol_filter(pre_smoothed, main_window, min(poly_order, main_window-1))
            else:
                final_signal = pre_smoothed
            
            return final_signal
    
    # Standard smoothing for normal resolution data
    window_length = min(window_length, len(signal))
    poly_order = min(poly_order, window_length - 1)
    
    if window_length < 3:
        return signal.copy()
    
    try:
        return savgol_filter(signal, window_length, poly_order)
    except:
        return signal.copy()


def smooth_signal(signal, window_length, poly_order=2):
    """
    Smooth signal using Savitzky-Golay filter
    
    Parameters:
        signal (np.ndarray): Input signal
        window_length (int): Length of smoothing window (must be odd)
        poly_order (int): Order of polynomial for fitting
    
    Returns:
        np.ndarray: Smoothed signal
    """
    # Check if this looks like high-resolution data that might benefit from adaptive smoothing
    if len(signal) > 200:  # High resolution indicator
        return smooth_signal_adaptive(signal, window_length, poly_order, high_resolution_mode=True)
    else:
        return smooth_signal_adaptive(signal, window_length, poly_order, high_resolution_mode=False)


def detect_outliers(signal, method='zscore', threshold=3.0):
    """
    Detect outliers in signal using specified method
    
    Parameters:
        signal (np.ndarray): Input signal
        method (str): Method for outlier detection ('zscore', 'iqr')
        threshold (float): Threshold for outlier detection
    
    Returns:
        np.ndarray: Boolean array indicating outliers
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
        raise ValueError(f"Unknown outlier detection method: {method}")


def interpolate_signal(T, signal, method='linear', num_points=None):
    """
    Interpolate signal to higher resolution
    
    Parameters:
        T (np.ndarray): Temperature array
        signal (np.ndarray): Signal array
        method (str): Interpolation method ('linear', 'cubic')
        num_points (int): Number of points for interpolated signal (if None, uses 3x original)
    
    Returns:
        tuple: (T_interp, signal_interp) - interpolated temperature and signal arrays
    """
    from scipy.interpolate import interp1d
    
    if len(T) != len(signal) or len(T) < 2:
        return T.copy(), signal.copy()
    
    if num_points is None:
        num_points = len(T) * 3
    
    # Create interpolation function
    try:
        f_interp = interp1d(T, signal, kind=method, bounds_error=False, fill_value='extrapolate')
        
        # Create new temperature array
        T_interp = np.linspace(T.min(), T.max(), num_points)
        signal_interp = f_interp(T_interp)
        
        return T_interp, signal_interp
        
    except:
        # Fallback to original data if interpolation fails
        return T.copy(), signal.copy() 