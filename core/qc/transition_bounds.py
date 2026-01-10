#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Transition Bounds Detection
============================
检测热力学转变的onset和offset温度边界

Used for:
- Validating temperature window selection (Tab 2)
- Detecting transition presence (Tab 1 QC)
- Onset/Offset reporting
"""

import numpy as np
from typing import Tuple, Optional
from scipy.ndimage import gaussian_filter1d


def detect_transition_bounds(
    T: np.ndarray,
    F: np.ndarray,
    Tm: float,
    method: str = 'derivative',
    sigma: float = 2.0,
    threshold_fraction: float = 0.1
) -> Tuple[Optional[float], Optional[float]]:
    """
    检测转变的onset和offset温度

    Args:
        T: Temperature array (°C)
        F: Fluorescence signal array
        Tm: Melting temperature (°C)
        method: Detection method ('derivative', 'threshold', 'curvature')
        sigma: Gaussian smoothing parameter for derivative
        threshold_fraction: Fraction of max derivative for threshold

    Returns:
        (onset, offset): Tuple of onset and offset temperatures (°C)
                        Returns (None, None) if detection fails
    """
    if len(T) < 10 or len(F) < 10:
        return None, None

    if np.isnan(Tm):
        return None, None

    try:
        if method == 'derivative':
            return _detect_by_derivative(T, F, Tm, sigma, threshold_fraction)
        elif method == 'threshold':
            return _detect_by_threshold(T, F, Tm)
        elif method == 'curvature':
            return _detect_by_curvature(T, F, Tm, sigma)
        else:
            # Default: use derivative method
            return _detect_by_derivative(T, F, Tm, sigma, threshold_fraction)

    except Exception:
        # Fallback: use simple heuristic
        return _simple_heuristic(T, Tm)


def _detect_by_derivative(
    T: np.ndarray,
    F: np.ndarray,
    Tm: float,
    sigma: float,
    threshold_fraction: float
) -> Tuple[Optional[float], Optional[float]]:
    """
    使用一阶导数检测onset/offset

    Onset: temperature where dF/dT rises above threshold (before Tm)
    Offset: temperature where dF/dT falls below threshold (after Tm)
    """
    # Smooth signal
    F_smooth = gaussian_filter1d(F, sigma=sigma)

    # Calculate first derivative
    dF_dT = np.gradient(F_smooth, T)

    # Find Tm index
    tm_idx = np.argmin(np.abs(T - Tm))

    # Threshold: fraction of max derivative near Tm
    # Look within ±10°C of Tm for max derivative
    window_start = max(0, tm_idx - 20)
    window_end = min(len(T), tm_idx + 20)
    max_deriv = np.abs(dF_dT[window_start:window_end]).max()

    if max_deriv < 1e-6:
        # No significant derivative, no transition
        return None, None

    deriv_threshold = threshold_fraction * max_deriv

    # Find onset (before Tm)
    onset = None
    for i in range(tm_idx, -1, -1):
        if np.abs(dF_dT[i]) < deriv_threshold:
            if i < len(T) - 1:
                onset = T[i + 1]  # First point above threshold
            break

    # Find offset (after Tm)
    offset = None
    for i in range(tm_idx, len(T)):
        if np.abs(dF_dT[i]) < deriv_threshold:
            if i > 0:
                offset = T[i - 1]  # Last point above threshold
            break

    return onset, offset


def _detect_by_threshold(
    T: np.ndarray,
    F: np.ndarray,
    Tm: float,
    progress_threshold: float = 0.1
) -> Tuple[Optional[float], Optional[float]]:
    """
    使用信号阈值检测onset/offset

    Onset: temperature where signal reaches 10% of total change
    Offset: temperature where signal reaches 90% of total change
    """
    # Normalize signal to 0-1
    F_min = F.min()
    F_max = F.max()

    if F_max - F_min < 1e-6:
        return None, None

    F_norm = (F - F_min) / (F_max - F_min)

    # Find Tm index
    tm_idx = np.argmin(np.abs(T - Tm))

    # Find onset (10% of transition)
    onset = None
    for i in range(tm_idx):
        if F_norm[i] >= progress_threshold:
            onset = T[i]
            break

    # Find offset (90% of transition)
    offset = None
    for i in range(tm_idx, len(T)):
        if F_norm[i] >= (1.0 - progress_threshold):
            offset = T[i]
            break

    return onset, offset


def _detect_by_curvature(
    T: np.ndarray,
    F: np.ndarray,
    Tm: float,
    sigma: float
) -> Tuple[Optional[float], Optional[float]]:
    """
    使用曲率(二阶导数)检测onset/offset

    Onset: local maximum of curvature before Tm
    Offset: local maximum of curvature after Tm
    """
    # Smooth signal
    F_smooth = gaussian_filter1d(F, sigma=sigma)

    # Calculate second derivative
    dF_dT = np.gradient(F_smooth, T)
    d2F_dT2 = np.gradient(dF_dT, T)

    # Find Tm index
    tm_idx = np.argmin(np.abs(T - Tm))

    # Find onset (local max curvature before Tm)
    onset = None
    curvature_before = np.abs(d2F_dT2[:tm_idx])
    if len(curvature_before) > 2:
        # Find local maxima
        peaks = []
        for i in range(1, len(curvature_before) - 1):
            if (curvature_before[i] > curvature_before[i - 1] and
                curvature_before[i] > curvature_before[i + 1]):
                peaks.append(i)

        if peaks:
            # Use the peak closest to Tm
            onset_idx = peaks[-1]
            onset = T[onset_idx]

    # Find offset (local max curvature after Tm)
    offset = None
    curvature_after = np.abs(d2F_dT2[tm_idx:])
    if len(curvature_after) > 2:
        peaks = []
        for i in range(1, len(curvature_after) - 1):
            if (curvature_after[i] > curvature_after[i - 1] and
                curvature_after[i] > curvature_after[i + 1]):
                peaks.append(i)

        if peaks:
            # Use the peak closest to Tm
            offset_idx = tm_idx + peaks[0]
            offset = T[offset_idx]

    return onset, offset


def _simple_heuristic(T: np.ndarray, Tm: float) -> Tuple[float, float]:
    """
    简单启发式: Tm ± 10°C

    Used as fallback when detection fails
    """
    onset = Tm - 10.0
    offset = Tm + 10.0

    # Clip to data range
    onset = max(T.min(), onset)
    offset = min(T.max(), offset)

    return onset, offset


def validate_window_in_transition(
    T_window_start: float,
    T_window_end: float,
    onset: Optional[float],
    offset: Optional[float],
    tolerance: float = 5.0
) -> bool:
    """
    验证温度窗口是否在转变区域内

    Args:
        T_window_start: Window start temperature (°C)
        T_window_end: Window end temperature (°C)
        onset: Transition onset temperature (°C)
        offset: Transition offset temperature (°C)
        tolerance: Tolerance for window boundaries (°C)

    Returns:
        True if window is within [onset - tolerance, offset + tolerance]
    """
    if onset is None or offset is None:
        # Cannot validate without bounds
        return True  # Assume valid

    # Window should be mostly within [onset, offset] with tolerance
    if T_window_start < onset - tolerance:
        return False

    if T_window_end > offset + tolerance:
        return False

    return True


def calculate_transition_width(onset: Optional[float], offset: Optional[float]) -> Optional[float]:
    """
    计算转变宽度

    Args:
        onset: Onset temperature (°C)
        offset: Offset temperature (°C)

    Returns:
        Transition width (°C), or None if onset/offset not available
    """
    if onset is None or offset is None:
        return None

    return offset - onset
