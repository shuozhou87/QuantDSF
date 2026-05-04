#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gaussian Deconvolution Module
==============================
Multi-peak detection and deconvolution for derivative curves.
Supports dual-peak analysis for multi-domain proteins (e.g., LAMP2)
and multi-component systems (e.g., PROTAC ternary complexes).

Ported from QuantDSF v1 gaussian_analysis.py with improvements.
"""

import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from typing import List, Dict, Tuple, Optional


def gaussian(x: np.ndarray, amp: float, cen: float, wid: float) -> np.ndarray:
    """Single Gaussian peak function."""
    return amp * np.exp(-(x - cen)**2 / (2 * wid**2))


def dual_gaussian(x: np.ndarray, *params) -> np.ndarray:
    """
    Sum of two Gaussian peaks plus a constant baseline.

    Parameters:
        x: temperature array
        params: [amp1, cen1, wid1, amp2, cen2, wid2, baseline]
    """
    amp1, cen1, wid1, amp2, cen2, wid2, baseline = params
    return (gaussian(x, amp1, cen1, wid1) +
            gaussian(x, amp2, cen2, wid2) +
            baseline)


def single_gaussian_with_baseline(x: np.ndarray, *params) -> np.ndarray:
    """
    Single Gaussian peak plus a constant baseline.

    Parameters:
        x: temperature array
        params: [amp, cen, wid, baseline]
    """
    amp, cen, wid, baseline = params
    return gaussian(x, amp, cen, wid) + baseline


def detect_peak_candidates(
    T: np.ndarray,
    derivative: np.ndarray,
    min_prominence_fraction: float = 0.05
) -> List[Dict]:
    """
    Detect candidate peaks in the derivative curve using scipy.find_peaks.

    Searches for both positive peaks (dips in fluorescence = unfolding for ratio)
    and negative peaks (dips in raw fluorescence channels).

    Parameters:
        T: temperature array
        derivative: dF/dT array
        min_prominence_fraction: minimum prominence as fraction of total range

    Returns:
        List of candidate dicts sorted by prominence (descending),
        each with keys: index, temperature, value, prominence, width_sigma, is_positive
    """
    candidates = []
    avg_spacing = np.mean(np.diff(T)) if len(T) > 1 else 1.0
    value_range = np.ptp(derivative)

    if value_range < 1e-10:
        return candidates

    prominence_threshold = min_prominence_fraction * value_range

    # Find positive peaks (for ratio channel where unfolding = increase in dF/dT)
    pos_indices, pos_props = find_peaks(
        derivative,
        prominence=prominence_threshold,
        width=(3, None),
        rel_height=0.5
    )
    for i, idx in enumerate(pos_indices):
        fwhm_points = pos_props.get('widths', np.array([5.0]))[i]
        sigma = (fwhm_points * avg_spacing) / 2.35482  # FWHM to sigma
        candidates.append({
            'index': idx,
            'temperature': T[idx],
            'value': derivative[idx],
            'prominence': pos_props['prominences'][i],
            'width_sigma': np.clip(sigma, 0.2, 10.0),
            'is_positive': True
        })

    # Find negative peaks (dips — for 330/350nm channels)
    neg_indices, neg_props = find_peaks(
        -derivative,
        prominence=prominence_threshold,
        width=(3, None),
        rel_height=0.5
    )
    for i, idx in enumerate(neg_indices):
        fwhm_points = neg_props.get('widths', np.array([5.0]))[i]
        sigma = (fwhm_points * avg_spacing) / 2.35482
        candidates.append({
            'index': idx,
            'temperature': T[idx],
            'value': derivative[idx],
            'prominence': neg_props['prominences'][i],
            'width_sigma': np.clip(sigma, 0.2, 10.0),
            'is_positive': False
        })

    # Sort by prominence (most prominent first)
    candidates.sort(key=lambda c: c['prominence'], reverse=True)
    return candidates


def deconvolute_dual_peaks(
    T: np.ndarray,
    derivative: np.ndarray,
    temp_range: Optional[Tuple[float, float]] = None
) -> Dict:
    """
    Deconvolute a derivative curve into exactly two Gaussian peaks.

    This is the main entry point for dual-peak analysis. It:
    1. Detects the signal region adaptively
    2. Finds candidate peaks via scipy.find_peaks
    3. Fits two Gaussians + baseline to the derivative curve
    4. Returns per-peak parameters and fit quality

    Parameters:
        T: full temperature array
        derivative: dF/dT array (same length as T)
        temp_range: optional (min_temp, max_temp) to restrict fitting region

    Returns:
        Dict with keys:
            success: bool
            peaks: list of 2 dicts, each with {tm, amplitude, width, area, gaussian_curve}
            baseline: float
            fit_r_squared: float
            T_fit: temperature array used for fitting
            fitted_curve: sum of both Gaussians + baseline
            individual_curves: list of 2 arrays (each Gaussian separately)
            error: str (if success=False)
    """
    result = {
        'success': False,
        'peaks': [],
        'baseline': 0.0,
        'fit_r_squared': 0.0,
        'T_fit': np.array([]),
        'fitted_curve': np.array([]),
        'individual_curves': [],
        'error': ''
    }

    # --- Step 1: Determine fitting region ---
    if temp_range:
        mask = (T >= temp_range[0]) & (T <= temp_range[1])
        T_fit = T[mask]
        deriv_fit = derivative[mask]
    else:
        T_fit, deriv_fit = _adaptive_fitting_range(T, derivative)

    if len(T_fit) < 10:
        result['error'] = 'Insufficient data points in fitting range'
        return result

    # --- Step 2: Find candidate peaks ---
    candidates = detect_peak_candidates(T_fit, deriv_fit)

    if len(candidates) < 2:
        result['error'] = f'Only {len(candidates)} peak(s) detected; need at least 2 for dual-peak analysis'
        return result

    # Determine signal direction for unfolding transitions:
    # For raw fluorescence (330/350nm): unfolding = negative dips in dF/dT
    # For ratio channel: unfolding = positive peaks in dF/dT
    # Strategy: try negative peaks first (raw channels), then positive (ratio)
    neg_candidates = [c for c in candidates if not c['is_positive']]
    pos_candidates = [c for c in candidates if c['is_positive']]

    # Prefer negative peaks (more common in raw fluorescence channels)
    if len(neg_candidates) >= 2:
        working_candidates = neg_candidates
    elif len(pos_candidates) >= 2:
        working_candidates = pos_candidates
    else:
        result['error'] = f'Need at least 2 same-sign peaks; found {len(neg_candidates)} negative, {len(pos_candidates)} positive'
        return result

    # Take top 2 by prominence, sorted by temperature
    top2 = sorted(working_candidates[:2], key=lambda c: c['temperature'])

    # --- Step 3: Build initial guesses and bounds ---
    p0 = [
        top2[0]['value'], top2[0]['temperature'], top2[0]['width_sigma'],  # peak 1
        top2[1]['value'], top2[1]['temperature'], top2[1]['width_sigma'],  # peak 2
        _estimate_baseline(T_fit, deriv_fit)                               # baseline
    ]

    lower_bounds = [
        -np.inf, T_fit[0], 0.1,      # peak 1: amp, center, width
        -np.inf, T_fit[0], 0.1,      # peak 2
        -np.inf                        # baseline
    ]
    upper_bounds = [
        np.inf, T_fit[-1], 15.0,
        np.inf, T_fit[-1], 15.0,
        np.inf
    ]

    # --- Step 4: Fit dual Gaussian ---
    try:
        popt, pcov = curve_fit(
            dual_gaussian, T_fit, deriv_fit,
            p0=p0,
            bounds=(lower_bounds, upper_bounds),
            maxfev=10000
        )
    except Exception as e:
        result['error'] = f'Curve fitting failed: {str(e)}'
        return result

    # --- Step 5: Extract results ---
    amp1, cen1, wid1, amp2, cen2, wid2, baseline = popt

    # Compute fitted curves
    fitted_total = dual_gaussian(T_fit, *popt)
    curve1 = gaussian(T_fit, amp1, cen1, wid1) + baseline / 2
    curve2 = gaussian(T_fit, amp2, cen2, wid2) + baseline / 2

    # R² of the fit
    ss_res = np.sum((deriv_fit - fitted_total) ** 2)
    ss_tot = np.sum((deriv_fit - np.mean(deriv_fit)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Sort peaks by temperature
    peaks_raw = [
        {'amplitude': amp1, 'center': cen1, 'width': wid1, 'curve': curve1},
        {'amplitude': amp2, 'center': cen2, 'width': wid2, 'curve': curve2}
    ]
    peaks_raw.sort(key=lambda p: p['center'])

    peaks_out = []
    individual_curves = []
    for i, p in enumerate(peaks_raw):
        area = abs(p['amplitude']) * p['width'] * np.sqrt(2 * np.pi)
        peaks_out.append({
            'tm': float(p['center']),
            'amplitude': float(p['amplitude']),
            'width': float(p['width']),
            'area': float(area),
            'peak_label': f"Peak {i+1}"
        })
        individual_curves.append(p['curve'])

    result.update({
        'success': True,
        'peaks': peaks_out,
        'baseline': float(baseline),
        'fit_r_squared': float(r_squared),
        'T_fit': T_fit,
        'fitted_curve': fitted_total,
        'individual_curves': individual_curves,
        'popt': popt,
        'error': ''
    })

    return result


def match_peaks_across_concentrations(
    all_peaks: List[List[Dict]],
    target_peak_index: int = 0
) -> List[Optional[float]]:
    """
    Track a specific peak across a concentration series.

    Uses nearest-temperature matching: for each concentration, find the peak
    closest to the target peak's Tm at the previous concentration.

    Parameters:
        all_peaks: list of peak lists, one per concentration.
                   Each inner list has dicts with 'tm' key.
        target_peak_index: which peak to track (0 = lower Tm, 1 = higher Tm)

    Returns:
        List of Tm values (one per concentration), or None where tracking failed
    """
    if not all_peaks:
        return []

    tracked_tms = []

    # Initialize from first concentration
    first_peaks = all_peaks[0]
    if len(first_peaks) > target_peak_index:
        current_tm = first_peaks[target_peak_index]['tm']
        tracked_tms.append(current_tm)
    else:
        tracked_tms.append(None)
        current_tm = None

    # Track across remaining concentrations
    for peaks in all_peaks[1:]:
        if current_tm is None or len(peaks) == 0:
            tracked_tms.append(None)
            continue

        # Find nearest peak to current tracking position
        distances = [abs(p['tm'] - current_tm) for p in peaks]
        nearest_idx = int(np.argmin(distances))

        # Sanity check: don't jump more than 15°C between concentrations
        if distances[nearest_idx] < 15.0:
            current_tm = peaks[nearest_idx]['tm']
            tracked_tms.append(current_tm)
        else:
            tracked_tms.append(None)

    return tracked_tms


# ---- Internal helpers ----

def _adaptive_fitting_range(
    T: np.ndarray,
    derivative: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Automatically detect the signal region of the derivative curve.
    Focuses on the region containing significant peaks, with some context.
    """
    abs_deriv = np.abs(derivative)
    max_signal = np.max(abs_deriv)

    if max_signal < 1e-10:
        return T, derivative

    # Find core signal region (>30% of max)
    core_mask = abs_deriv >= 0.3 * max_signal
    core_indices = np.where(core_mask)[0]

    if len(core_indices) == 0:
        return T, derivative

    # Find broader context region (>5% of max)
    context_mask = abs_deriv >= 0.05 * max_signal
    context_indices = np.where(context_mask)[0]

    # Expand around core with context
    start_idx = max(0, context_indices[0] - 5)
    end_idx = min(len(T), context_indices[-1] + 5)

    # Ensure minimum range
    if end_idx - start_idx < 20:
        center = (core_indices[0] + core_indices[-1]) // 2
        start_idx = max(0, center - 15)
        end_idx = min(len(T), center + 15)

    return T[start_idx:end_idx], derivative[start_idx:end_idx]


def _estimate_baseline(T: np.ndarray, derivative: np.ndarray) -> float:
    """Estimate baseline from edge regions of the fitting range."""
    if len(T) < 10:
        return float(np.median(derivative))

    n_edge = max(3, int(len(T) * 0.15))
    edge_values = np.concatenate([derivative[:n_edge], derivative[-n_edge:]])
    return float(np.median(edge_values))
