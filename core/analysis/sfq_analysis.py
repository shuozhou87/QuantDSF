#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Static Fluorescence Quenching / Enhancement (SFQ/SFE) Analysis
===============================================================

Detects and quantifies static fluorescence changes (quenching or enhancement)
in dose-series data by analyzing cold-window (native state) fluorescence
intensity as a function of ligand concentration.

Core approach:
- Extract cold-window fluorescence (median of first 5 temperature points)
- Compare linear vs 4PL models using AIC
- Calculate Saturation Index (SI) to verify plateau at high concentrations
- Report EC50_app if saturable binding is detected

Output states: Not detected / Detected / Detected (caution)
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import linregress
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SFQChannelResult:
    """Result for a single channel SFQ analysis"""
    status: str  # 'Not detected', 'Detected', 'Detected (caution)'
    mode: Optional[str]  # 'Quenching', 'Enhancement', or None
    ec50_app: Optional[float]  # Apparent EC50 in M
    ec50_app_str: Optional[str]  # Formatted EC50 string
    span: float  # Dynamic range (%)
    delta_aic: float  # AIC_linear - AIC_4PL (positive = 4PL better)
    saturation_index: Optional[float]  # SI value
    r2_linear: float  # R² of linear fit
    r2_4pl: float  # R² of 4PL fit
    linear_params: Dict[str, float]  # slope, intercept
    fourpl_params: Optional[Dict[str, float]]  # Bottom, Top, EC50, Hill
    notes: str  # Explanation/warning message


@dataclass
class SFQDatasetResult:
    """Aggregated SFQ result for the dataset"""
    dataset_status: str  # 'Not detected', 'Detected', 'Detected (caution)'
    channel_result: SFQChannelResult  # Single channel result
    channel_name: str  # '330' or '350'
    concentrations: List[float]
    cold_fluorescence: List[float]
    linear_fit_y: List[float]
    fourpl_fit_y: Optional[List[float]]


# ============================================================================
# Model Functions
# ============================================================================

def hill_4pl(x: np.ndarray, bottom: float, top: float, ec50: float, hill: float) -> np.ndarray:
    """
    4-Parameter Logistic (Hill) model.

    y = Bottom + (Top - Bottom) / (1 + (EC50/x)^Hill)

    Note: Uses EC50/x form so increasing x gives sigmoidal increase when Hill > 0
    """
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        ratio = np.power(ec50 / x, hill)
        result = bottom + (top - bottom) / (1 + ratio)
        return np.nan_to_num(result, nan=bottom, posinf=top, neginf=bottom)


def linear_logc(log_c: np.ndarray, slope: float, intercept: float) -> np.ndarray:
    """Linear model in log10(concentration) space: y = slope * log10(C) + intercept"""
    return slope * log_c + intercept


# ============================================================================
# Core Analysis Functions
# ============================================================================

def calculate_cold_fluorescence(
    temperatures: np.ndarray,
    fluorescence: np.ndarray,
    n_points: int = 5
) -> float:
    """
    Calculate cold-window fluorescence as median of first N temperature points.

    Args:
        temperatures: Temperature array
        fluorescence: Fluorescence intensity array
        n_points: Number of points for cold window (default: 5)

    Returns:
        Median fluorescence in cold window
    """
    # Sort by temperature to ensure we get the coldest points
    sort_idx = np.argsort(temperatures)
    cold_idx = sort_idx[:n_points]
    cold_f = fluorescence[cold_idx]
    return float(np.median(cold_f))


def calculate_span(
    cold_fluorescence: np.ndarray,
    n_low_conc: int = 2
) -> float:
    """
    Calculate dynamic range (span) as percentage.

    span = (max(y) - min(y)) / median(y at lowest concentrations)

    Args:
        cold_fluorescence: Array of cold fluorescence values sorted by concentration
        n_low_conc: Number of lowest concentration points for baseline

    Returns:
        Span as percentage (0-100+)
    """
    y = np.array(cold_fluorescence)
    if len(y) < n_low_conc + 1:
        return 0.0

    y_low = y[:n_low_conc]
    baseline = np.median(y_low)

    if baseline <= 0:
        return 0.0

    span = (np.max(y) - np.min(y)) / baseline * 100.0
    return float(span)


def fit_linear_model(
    concentrations: np.ndarray,
    cold_fluorescence: np.ndarray
) -> Dict[str, Any]:
    """
    Fit linear model in log10(concentration) space.

    Args:
        concentrations: Concentration array in M
        cold_fluorescence: Cold fluorescence values

    Returns:
        Dict with slope, intercept, r2, aic, residuals
    """
    # Filter valid data
    valid_mask = (concentrations > 0) & np.isfinite(concentrations) & np.isfinite(cold_fluorescence)
    conc = concentrations[valid_mask]
    y = cold_fluorescence[valid_mask]

    if len(conc) < 3:
        return {'success': False, 'error': 'Insufficient data points'}

    log_c = np.log10(conc)

    # Linear regression
    slope, intercept, r_value, p_value, std_err = linregress(log_c, y)

    y_pred = linear_logc(log_c, slope, intercept)
    residuals = y - y_pred
    ss_res = np.sum(residuals ** 2)
    n = len(y)
    k = 2  # Number of parameters

    # AIC calculation
    if ss_res > 0:
        aic = n * np.log(ss_res / n) + 2 * k
    else:
        aic = -np.inf

    return {
        'success': True,
        'slope': float(slope),
        'intercept': float(intercept),
        'r2': float(r_value ** 2),
        'aic': float(aic),
        'residuals': residuals,
        'y_pred': y_pred,
        'n': n,
        'k': k
    }


def fit_4pl_model(
    concentrations: np.ndarray,
    cold_fluorescence: np.ndarray
) -> Dict[str, Any]:
    """
    Fit 4-Parameter Logistic (Hill) model.

    Args:
        concentrations: Concentration array in M
        cold_fluorescence: Cold fluorescence values

    Returns:
        Dict with Bottom, Top, EC50, Hill, r2, aic, etc.
    """
    # Filter valid data
    valid_mask = (concentrations > 0) & np.isfinite(concentrations) & np.isfinite(cold_fluorescence)
    conc = concentrations[valid_mask]
    y = cold_fluorescence[valid_mask]

    if len(conc) < 4:
        return {'success': False, 'error': 'Insufficient data points for 4PL'}

    # Initial parameter guesses
    y_min, y_max = np.min(y), np.max(y)
    y_mid = (y_min + y_max) / 2

    # Find approximate EC50 (concentration where y is closest to midpoint)
    mid_idx = np.argmin(np.abs(y - y_mid))
    ec50_init = conc[mid_idx] if mid_idx > 0 else np.median(conc)

    # Determine direction (quenching vs enhancement)
    # If fluorescence decreases with concentration -> quenching
    low_conc_mean = np.mean(y[:max(2, len(y)//4)])
    high_conc_mean = np.mean(y[-max(2, len(y)//4):])

    if high_conc_mean < low_conc_mean:
        # Quenching: Top > Bottom
        bottom_init = y_min
        top_init = y_max
        hill_init = 1.0
    else:
        # Enhancement: Top > Bottom (signal increases)
        bottom_init = y_min
        top_init = y_max
        hill_init = 1.0

    p0 = [bottom_init, top_init, ec50_init, hill_init]

    # Bounds
    conc_min, conc_max = np.min(conc), np.max(conc)
    bounds = (
        [y_min * 0.5, y_min * 0.5, conc_min * 1e-3, 0.1],  # Lower bounds
        [y_max * 2.0, y_max * 2.0, conc_max * 1e3, 10.0]   # Upper bounds
    )

    try:
        popt, pcov = curve_fit(
            hill_4pl, conc, y,
            p0=p0,
            bounds=bounds,
            maxfev=5000
        )

        bottom, top, ec50, hill = popt

        # Calculate fit quality
        y_pred = hill_4pl(conc, *popt)
        residuals = y - y_pred
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        n = len(y)
        k = 4  # Number of parameters

        # AIC calculation
        if ss_res > 0:
            aic = n * np.log(ss_res / n) + 2 * k
        else:
            aic = -np.inf

        # Determine mode
        if top > bottom:
            mode = 'Enhancement'
        else:
            mode = 'Quenching'

        return {
            'success': True,
            'bottom': float(bottom),
            'top': float(top),
            'ec50': float(ec50),
            'hill': float(hill),
            'r2': float(r2),
            'aic': float(aic),
            'residuals': residuals,
            'y_pred': y_pred,
            'mode': mode,
            'n': n,
            'k': k,
            'pcov': pcov
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def calculate_saturation_index(
    concentrations: np.ndarray,
    cold_fluorescence: np.ndarray,
    n_high: int = 3,
    n_mid: int = 4
) -> Optional[float]:
    """
    Calculate Saturation Index (SI) to assess plateau at high concentrations.

    SI = |slope_high| / (|slope_mid| + eps)

    Lower SI indicates better plateau (more saturable behavior).

    Args:
        concentrations: Concentration array in M (sorted)
        cold_fluorescence: Cold fluorescence values (sorted by concentration)
        n_high: Number of high concentration points
        n_mid: Number of mid-range points

    Returns:
        SI value or None if insufficient data
    """
    n = len(concentrations)
    if n < 5:
        return None

    # Ensure data is sorted by concentration
    sort_idx = np.argsort(concentrations)
    conc = concentrations[sort_idx]
    y = cold_fluorescence[sort_idx]

    # Filter valid
    valid = (conc > 0) & np.isfinite(conc) & np.isfinite(y)
    conc = conc[valid]
    y = y[valid]
    log_c = np.log10(conc)

    n = len(conc)
    if n < 5:
        return None

    # Adjust window sizes if needed
    n_high = min(n_high, max(2, n // 3))
    n_mid = min(n_mid, max(2, n // 2))

    if n_high < 2 or n_mid < 2:
        return None

    # High concentration window (last n_high points)
    high_log_c = log_c[-n_high:]
    high_y = y[-n_high:]

    # Mid window: find the STEEPEST region using sliding window
    # This is more robust than fixed middle portion
    best_mid_slope = 0.0
    window_size = min(n_mid, n - 2)

    for start in range(n - window_size - 1):  # Don't include last n_high points
        end = start + window_size
        if end >= n - n_high:  # Stop before high concentration region
            break
        window_log_c = log_c[start:end]
        window_y = y[start:end]
        if len(window_log_c) >= 2:
            try:
                slope, _, _, _, _ = linregress(window_log_c, window_y)
                if abs(slope) > abs(best_mid_slope):
                    best_mid_slope = slope
            except:
                pass

    # Fallback if sliding window didn't find anything
    if abs(best_mid_slope) < 1e-10:
        mid_start = n // 4
        mid_end = max(mid_start + 2, 3 * n // 4)
        if mid_end > n - n_high:
            mid_end = n - n_high
        if mid_end > mid_start + 1:
            mid_log_c = log_c[mid_start:mid_end]
            mid_y = y[mid_start:mid_end]
            try:
                best_mid_slope, _, _, _, _ = linregress(mid_log_c, mid_y)
            except:
                pass

    if len(high_log_c) < 2 or abs(best_mid_slope) < 1e-10:
        return None

    # Fit linear in high region
    try:
        slope_high, _, _, _, _ = linregress(high_log_c, high_y)

        eps = 1e-10
        si = abs(slope_high) / (abs(best_mid_slope) + eps)
        return float(si)
    except:
        return None


def analyze_sfq_channel(
    concentrations: np.ndarray,
    cold_fluorescence: np.ndarray,
    channel_name: str,
    span_threshold: float = 30.0,
    delta_aic_strong: float = 10.0,
    delta_aic_weak: float = 2.0,
    si_strong: float = 0.3,
    si_caution: float = 0.6
) -> SFQChannelResult:
    """
    Perform complete SFQ analysis for a single channel.

    Args:
        concentrations: Concentration array in M
        cold_fluorescence: Cold fluorescence values
        channel_name: '330' or '350'
        span_threshold: Minimum span (%) required
        delta_aic_strong: ΔAIC threshold for strong 4PL support
        delta_aic_weak: ΔAIC threshold for weak 4PL support
        si_strong: SI threshold for strong plateau
        si_caution: SI threshold for caution

    Returns:
        SFQChannelResult with all analysis metrics
    """
    # Sort by concentration
    sort_idx = np.argsort(concentrations)
    conc = concentrations[sort_idx]
    cold_f = np.array(cold_fluorescence)[sort_idx]

    # Calculate span
    span = calculate_span(cold_f, n_low_conc=2)

    # Default result for "Not detected"
    default_result = SFQChannelResult(
        status='Not detected',
        mode=None,
        ec50_app=None,
        ec50_app_str=None,
        span=span,
        delta_aic=0.0,
        saturation_index=None,
        r2_linear=0.0,
        r2_4pl=0.0,
        linear_params={},
        fourpl_params=None,
        notes=''
    )

    # Check span threshold
    if span < span_threshold:
        default_result.notes = f"Insufficient dynamic range (span={span:.1f}% < {span_threshold}%)"
        return default_result

    # Fit linear model
    linear_result = fit_linear_model(conc, cold_f)
    if not linear_result['success']:
        default_result.notes = f"Linear fit failed: {linear_result.get('error', 'Unknown')}"
        return default_result

    # Fit 4PL model
    fourpl_result = fit_4pl_model(conc, cold_f)

    # Calculate delta AIC
    if fourpl_result['success']:
        delta_aic = linear_result['aic'] - fourpl_result['aic']  # Positive = 4PL better
    else:
        delta_aic = -np.inf

    # Calculate Saturation Index
    si = calculate_saturation_index(conc, cold_f)

    # Build result
    linear_params = {
        'slope': linear_result['slope'],
        'intercept': linear_result['intercept']
    }

    fourpl_params = None
    if fourpl_result['success']:
        fourpl_params = {
            'bottom': fourpl_result['bottom'],
            'top': fourpl_result['top'],
            'ec50': fourpl_result['ec50'],
            'hill': fourpl_result['hill']
        }

    # Determine status based on criteria
    status = 'Not detected'
    mode = None
    ec50_app = None
    ec50_app_str = None
    notes_parts = []

    if not fourpl_result['success']:
        status = 'Not detected'
        notes_parts.append(f"4PL fit failed: {fourpl_result.get('error', 'Unknown')}")
    elif delta_aic < delta_aic_weak:
        status = 'Not detected'
        notes_parts.append(f"Linear model fits equally well (ΔAIC={delta_aic:.1f})")
    else:
        # 4PL is at least somewhat better
        mode = fourpl_result['mode']
        ec50_app = fourpl_result['ec50']

        # Format EC50 string
        if ec50_app >= 1e-3:
            ec50_app_str = f"{ec50_app*1e3:.2f} mM"
        elif ec50_app >= 1e-6:
            ec50_app_str = f"{ec50_app*1e6:.2f} µM"
        elif ec50_app >= 1e-9:
            ec50_app_str = f"{ec50_app*1e9:.2f} nM"
        else:
            ec50_app_str = f"{ec50_app:.2e} M"

        if delta_aic >= delta_aic_strong:
            # Strong AIC support
            if si is not None and si < si_strong:
                status = 'Detected'
                notes_parts.append(f"Strong saturable signal ({mode})")
            elif si is not None and si < si_caution:
                status = 'Detected (caution)'
                notes_parts.append(f"Saturable signal detected but SI={si:.2f} suggests incomplete plateau")
            elif si is not None:
                status = 'Detected (caution)'
                notes_parts.append(f"Warning: SI={si:.2f} indicates continued linear drift at high concentrations")
            else:
                status = 'Detected'
                notes_parts.append(f"Saturable signal ({mode}), SI not calculable")
        else:
            # Weak AIC support (delta_aic_weak <= delta_aic < delta_aic_strong)
            status = 'Detected (caution)'
            notes_parts.append(f"Marginal evidence for saturation (ΔAIC={delta_aic:.1f})")

    return SFQChannelResult(
        status=status,
        mode=mode,
        ec50_app=ec50_app,
        ec50_app_str=ec50_app_str,
        span=span,
        delta_aic=float(delta_aic) if np.isfinite(delta_aic) else 0.0,
        saturation_index=si,
        r2_linear=linear_result['r2'],
        r2_4pl=fourpl_result['r2'] if fourpl_result['success'] else 0.0,
        linear_params=linear_params,
        fourpl_params=fourpl_params,
        notes='; '.join(notes_parts)
    )


def analyze_sfq_dataset(
    samples: List[Dict[str, Any]],
    channel: str,
    cold_window_points: int = 5
) -> Optional[SFQDatasetResult]:
    """
    Perform SFQ analysis on a dataset of samples.

    Args:
        samples: List of sample dicts with 'T', 'F', 'concentration' keys
        channel: '330', '350', or 'ratio'
        cold_window_points: Number of temperature points for cold window

    Returns:
        SFQDatasetResult or None if channel is 'ratio' or insufficient data
    """
    # SFQ only works for 330 or 350 channels
    channel_lower = channel.lower()
    if 'ratio' in channel_lower:
        return None

    # Determine channel name
    if '330' in channel_lower:
        channel_name = '330'
    elif '350' in channel_lower:
        channel_name = '350'
    else:
        return None

    # Extract cold fluorescence for each sample
    concentrations = []
    cold_fluorescence = []

    for sample in samples:
        conc = sample.get('concentration')
        T = sample.get('T')
        F = sample.get('F')

        if conc is None or conc <= 0 or T is None or F is None:
            continue

        T = np.array(T)
        F = np.array(F)

        if len(T) < cold_window_points or len(F) < cold_window_points:
            continue

        cold_f = calculate_cold_fluorescence(T, F, cold_window_points)
        concentrations.append(conc)
        cold_fluorescence.append(cold_f)

    if len(concentrations) < 4:
        return None

    concentrations = np.array(concentrations)
    cold_fluorescence = np.array(cold_fluorescence)

    # Sort by concentration
    sort_idx = np.argsort(concentrations)
    concentrations = concentrations[sort_idx]
    cold_fluorescence = cold_fluorescence[sort_idx]

    # Run channel analysis
    channel_result = analyze_sfq_channel(concentrations, cold_fluorescence, channel_name)

    # Generate fit curves for plotting
    log_c = np.log10(concentrations)
    log_c_fit = np.linspace(log_c.min(), log_c.max(), 100)
    conc_fit = 10 ** log_c_fit

    # Linear fit curve
    linear_fit_y = linear_logc(
        log_c_fit,
        channel_result.linear_params.get('slope', 0),
        channel_result.linear_params.get('intercept', 0)
    ).tolist()

    # 4PL fit curve
    fourpl_fit_y = None
    if channel_result.fourpl_params:
        fourpl_fit_y = hill_4pl(
            conc_fit,
            channel_result.fourpl_params['bottom'],
            channel_result.fourpl_params['top'],
            channel_result.fourpl_params['ec50'],
            channel_result.fourpl_params['hill']
        ).tolist()

    return SFQDatasetResult(
        dataset_status=channel_result.status,
        channel_result=channel_result,
        channel_name=channel_name,
        concentrations=concentrations.tolist(),
        cold_fluorescence=cold_fluorescence.tolist(),
        linear_fit_y=linear_fit_y,
        fourpl_fit_y=fourpl_fit_y
    )


def format_sfq_summary(result: Optional[SFQDatasetResult]) -> str:
    """
    Generate a summary message for UI display.

    Args:
        result: SFQDatasetResult or None

    Returns:
        Human-readable summary string
    """
    if result is None:
        return "SFQ analysis not available for ratio channel."

    cr = result.channel_result

    if cr.status == 'Not detected':
        return f"No significant static fluorescence change detected in F{result.channel_name}."

    mode_str = cr.mode or "change"
    if cr.status == 'Detected':
        return f"Static Fluorescence {mode_str} detected in F{result.channel_name}: EC50_app = {cr.ec50_app_str}"
    else:  # Detected (caution)
        return f"Possible Static Fluorescence {mode_str} in F{result.channel_name}: EC50_app = {cr.ec50_app_str} (interpret with caution)"
