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
    saturation_index: Optional[float]  # SI value (2-point window method)
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


def linear_c(c: np.ndarray, slope: float, intercept: float) -> np.ndarray:
    """Linear model in concentration space: y = slope * C + intercept (Lambert-Beer law)"""
    return slope * c + intercept


def derivative_4pl(c: float, bottom: float, top: float, ec50: float, hill: float) -> float:
    """
    Calculate derivative of 4PL model at concentration c.
    
    dy/dx = (Top - Bottom) * Hill * (EC50/x)^Hill / [x * (1 + (EC50/x)^Hill)^2]
    
    Args:
        c: Concentration value
        bottom, top, ec50, hill: 4PL parameters
    
    Returns:
        Derivative value (slope) at concentration c
    """
    if c <= 0:
        return 0.0
    
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        ratio = (ec50 / c) ** hill
        numerator = (top - bottom) * hill * ratio
        denominator = c * (1 + ratio) ** 2
        
        if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
            return 0.0
        
        return numerator / denominator


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
    Fit linear model in concentration space (Lambert-Beer law).
    
    F = slope * C + intercept
    
    This models non-specific absorption/quenching which should be proportional
    to concentration according to Lambert-Beer law.

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

    # Linear regression in concentration space (not log space)
    slope, intercept, r_value, p_value, std_err = linregress(conc, y)

    y_pred = linear_c(conc, slope, intercept)
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


def fit_piecewise_linear_model(
    concentrations: np.ndarray,
    cold_fluorescence: np.ndarray
) -> Dict[str, Any]:
    """
    Fit piecewise linear model in log-concentration space.
    
    F = {
      slope1 * log10(C) + intercept1,  if C < C_break
      slope2 * log10(C) + intercept2,  if C >= C_break
    }
    
    This models non-specific binding that shows distinct behavior in
    low-concentration (Lambert-Beer) and high-concentration (inner filter,
    aggregation, solubility limits) regimes.
    
    The breakpoint is automatically detected by minimizing total residual.

    Args:
        concentrations: Concentration array in M
        cold_fluorescence: Cold fluorescence values

    Returns:
        Dict with slopes, intercepts, breakpoint, r2, aic, residuals
    """
    # Filter valid data
    valid_mask = (concentrations > 0) & np.isfinite(concentrations) & np.isfinite(cold_fluorescence)
    conc = concentrations[valid_mask]
    y = cold_fluorescence[valid_mask]

    n = len(conc)
    if n < 5:  # Need at least 5 points for piecewise fitting
        return {'success': False, 'error': 'Insufficient data points'}

    # Sort by concentration
    sort_idx = np.argsort(conc)
    conc = conc[sort_idx]
    y = y[sort_idx]
    log_c = np.log10(conc)

    # Try different breakpoints and find the one with minimum total residual
    best_ssr = np.inf
    best_breakpoint_idx = None
    best_params = None
    
    # Search breakpoints from 30% to 70% of data range
    min_idx = max(2, int(n * 0.3))
    max_idx = min(n - 2, int(n * 0.7))
    
    for break_idx in range(min_idx, max_idx + 1):
        try:
            # Segment 1: low concentration
            log_c1 = log_c[:break_idx]
            y1 = y[:break_idx]
            
            # Segment 2: high concentration
            log_c2 = log_c[break_idx:]
            y2 = y[break_idx:]
            
            # Fit both segments
            if len(log_c1) >= 2 and len(log_c2) >= 2:
                slope1, intercept1, _, _, _ = linregress(log_c1, y1)
                slope2, intercept2, _, _, _ = linregress(log_c2, y2)
                
                # Calculate total residual
                y_pred1 = slope1 * log_c1 + intercept1
                y_pred2 = slope2 * log_c2 + intercept2
                
                ssr1 = np.sum((y1 - y_pred1) ** 2)
                ssr2 = np.sum((y2 - y_pred2) ** 2)
                total_ssr = ssr1 + ssr2
                
                if total_ssr < best_ssr:
                    best_ssr = total_ssr
                    best_breakpoint_idx = break_idx
                    best_params = {
                        'slope1': slope1,
                        'intercept1': intercept1,
                        'slope2': slope2,
                        'intercept2': intercept2,
                        'breakpoint_conc': conc[break_idx]
                    }
        except:
            continue
    
    if best_params is None:
        return {'success': False, 'error': 'Piecewise fitting failed'}
    
    # Calculate final predictions and metrics
    y_pred = np.zeros_like(y)
    y_pred[:best_breakpoint_idx] = best_params['slope1'] * log_c[:best_breakpoint_idx] + best_params['intercept1']
    y_pred[best_breakpoint_idx:] = best_params['slope2'] * log_c[best_breakpoint_idx:] + best_params['intercept2']
    
    residuals = y - y_pred
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    # AIC calculation (k=5: slope1, intercept1, slope2, intercept2, breakpoint)
    k = 5
    if ss_res > 0:
        aic = n * np.log(ss_res / n) + 2 * k
    else:
        aic = -np.inf

    return {
        'success': True,
        'slope1': float(best_params['slope1']),
        'intercept1': float(best_params['intercept1']),
        'slope2': float(best_params['slope2']),
        'intercept2': float(best_params['intercept2']),
        'breakpoint_conc': float(best_params['breakpoint_conc']),
        'breakpoint_idx': best_breakpoint_idx,
        'r2': float(r2),
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

    # Use consistent window size for both regions
    window_size = 2  # Changed to 2-point window per user request
    
    # Adjust if not enough data
    if n < window_size + 2:  # Need at least 4 points total
        return None
    
    n_high = min(window_size, n // 3)  # Last 2 points (or fewer if dataset is small)
    if n_high < 2:
        return None

    # High concentration window (last n_high points)
    high_log_c = log_c[-n_high:]
    high_y = y[-n_high:]

    # Mid window: find the STEEPEST region using sliding 2-point window
    # IMPORTANT: Exclude the high concentration region (last n_high points)
    best_mid_slope = 0.0
    best_mid_idx = None  # Track where we found the steepest slope
    search_end = n - n_high  # Stop BEFORE high concentration region
    
    if search_end < window_size:
        # Not enough points to search
        return None
    
    # Slide a 2-point window through the data, excluding high concentration region
    for start in range(search_end - window_size + 1):
        end = start + window_size
        if end > search_end:  # Double-check we don't overlap with high region
            break
        
        window_log_c = log_c[start:end]
        window_y = y[start:end]
        
        if len(window_log_c) >= 2:
            try:
                slope, _, _, _, _ = linregress(window_log_c, window_y)
                if abs(slope) > abs(best_mid_slope):
                    best_mid_slope = slope
                    best_mid_idx = start
            except:
                pass

    # Fallback: if no valid slope found, use a fixed middle region
    if abs(best_mid_slope) < 1e-10:
        mid_start = max(0, n // 4)
        mid_end = min(mid_start + window_size, search_end)
        if mid_end > mid_start + 1:
            mid_log_c = log_c[mid_start:mid_end]
            mid_y = y[mid_start:mid_end]
            try:
                best_mid_slope, _, _, _, _ = linregress(mid_log_c, mid_y)
                best_mid_idx = mid_start
            except:
                pass

    if len(high_log_c) < 2 or abs(best_mid_slope) < 1e-10:
        return None

    # Fit linear in high region
    try:
        slope_high, _, _, _, _ = linregress(high_log_c, high_y)

        eps = 1e-10
        si = abs(slope_high) / (abs(best_mid_slope) + eps)
        
        # DEBUG: Print slope information to understand SI > 1 cases
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[SI DEBUG] n_points={n}, n_high={n_high}, search_end={search_end}")
        logger.info(f"[SI DEBUG] High region: indices [{n-n_high}:{n}], slope_high={slope_high:.4f}")
        logger.info(f"[SI DEBUG] Mid region: indices [{best_mid_idx}:{best_mid_idx+window_size}], best_mid_slope={best_mid_slope:.4f}")
        logger.info(f"[SI DEBUG] SI = |{slope_high:.4f}| / |{best_mid_slope:.4f}| = {si:.4f}")
        
        return float(si)
    except:
        return None



def calculate_saturation_index_v2(
    concentrations: np.ndarray,
    fourpl_params: Dict[str, float]
) -> Optional[float]:
    """
    Calculate Saturation Index using 4PL curve derivatives (NEW METHOD).
    
    SI = |slope at highest conc| / |max slope across all conc|
    
    This method uses the analytical derivative of the 4PL curve rather than
    linear regression slopes, providing a more theoretically sound measure
    of saturation.
    
    Args:
        concentrations: Concentration array in M (sorted)
        fourpl_params: Dict with 'bottom', 'top', 'ec50', 'hill'
    
    Returns:
        SI value or None if calculation fails
    """
    try:
        bottom = fourpl_params['bottom']
        top = fourpl_params['top']
        ec50 = fourpl_params['ec50']
        hill = fourpl_params['hill']
        
        # Calculate derivative at all concentration points
        slopes = np.array([
            abs(derivative_4pl(c, bottom, top, ec50, hill)) 
            for c in concentrations
        ])
        
        # Filter out invalid values
        valid_slopes = slopes[np.isfinite(slopes) & (slopes > 0)]
        if len(valid_slopes) == 0:
            return None
        
        # Max slope (should be near EC50)
        max_slope = np.max(valid_slopes)
        
        # Slope at highest concentration
        highest_conc = np.max(concentrations)
        slope_high = abs(derivative_4pl(highest_conc, bottom, top, ec50, hill))
        
        if not np.isfinite(slope_high) or max_slope == 0:
            return None
        
        # SI
        si = slope_high / max_slope
        
        return float(si)
    except Exception:
        return None


def calculate_saturation_index_v3(
    concentrations: np.ndarray,
    cold_fluorescence: np.ndarray
) -> Optional[float]:
    """
    Calculate Saturation Index using ACTUAL data slopes (MOST ROBUST METHOD).
    
    SI = |slope at highest conc| / |max slope across all data|
    
    This method uses actual data point slopes rather than theoretical 4PL derivatives,
    making it more robust to fitting artifacts.
    
    Args:
        concentrations: Concentration array in M (sorted)
        cold_fluorescence: Cold fluorescence values (sorted by concentration)
    
    Returns:
        SI value or None if calculation fails
    """
    try:
        # Sort by concentration
        sort_idx = np.argsort(concentrations)
        conc = concentrations[sort_idx]
        y = cold_fluorescence[sort_idx]
        
        n = len(conc)
        if n < 5:
            return None
        
        # Calculate slopes between consecutive points (in concentration space)
        slopes = []
        for i in range(n - 1):
            dc = conc[i+1] - conc[i]
            dy = y[i+1] - y[i]
            if dc > 0:
                slope = abs(dy / dc)
                slopes.append(slope)
            else:
                slopes.append(0)
        
        if len(slopes) == 0:
            return None
        
        # Max slope (steepest region in actual data)
        max_slope = max(slopes)
        
        if max_slope == 0:
            return None
        
        # Slope at highest concentration region (average of last 2-3 slopes)
        n_high = min(3, max(2, n // 4))
        high_slopes = slopes[-(n_high-1):] if n_high > 1 else [slopes[-1]]
        slope_high = np.mean(high_slopes)
        
        si = slope_high / max_slope
        return float(si)
    except Exception:
        return None


def calculate_high_conc_residual(
    concentrations: np.ndarray,
    cold_fluorescence: np.ndarray,
    fourpl_params: Dict[str, float],
    n_high: int = 3
) -> Optional[float]:
    """
    Calculate relative residual at high concentration points.
    
    High residual indicates poor fit at saturation region, suggesting
    the data doesn't truly saturate despite good overall 4PL fit.
    
    Args:
        concentrations: Concentration array in M
        cold_fluorescence: Cold fluorescence values
        fourpl_params: 4PL parameters
        n_high: Number of high concentration points to check
    
    Returns:
        Relative residual (0-1+) or None if calculation fails
    """
    try:
        # Sort by concentration
        sort_idx = np.argsort(concentrations)
        conc = concentrations[sort_idx]
        y = cold_fluorescence[sort_idx]
        
        n = len(conc)
        if n < n_high:
            return None
        
        # Get highest concentration points
        high_conc = conc[-n_high:]
        high_y = y[-n_high:]
        
        # Predict using 4PL
        bottom = fourpl_params['bottom']
        top = fourpl_params['top']
        ec50 = fourpl_params['ec50']
        hill = fourpl_params['hill']
        
        high_predicted = hill_4pl(high_conc, bottom, top, ec50, hill)
        
        # Calculate residuals
        residuals = np.abs(high_y - high_predicted)
        mean_residual = np.mean(residuals)
        
        # Relative to signal range
        signal_range = abs(top - bottom)
        if signal_range == 0:
            return None
        
        relative_residual = mean_residual / signal_range
        
        return float(relative_residual)
    except Exception:
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

    # PREREQUISITE CHECK: Signal Change must be sufficient
    # Span = (max(F) - min(F)) / median(F_baseline) × 100%
    # This ensures there's enough fluorescence modulation to analyze
    if span < span_threshold:
        default_result.notes = f"Insufficient signal change (span={span:.1f}% < {span_threshold}%)"
        return default_result

    # Fit piecewise linear model (non-specific binding baseline)
    linear_result = fit_piecewise_linear_model(conc, cold_f)
    if not linear_result['success']:
        default_result.notes = f"Piecewise linear fit failed: {linear_result.get('error', 'Unknown')}"
        return default_result

    # Fit 4PL model
    fourpl_result = fit_4pl_model(conc, cold_f)

    # Calculate delta AIC
    if fourpl_result['success']:
        delta_aic = linear_result['aic'] - fourpl_result['aic']  # Positive = 4PL better
    else:
        delta_aic = -np.inf

    # Calculate Saturation Index using finalized 2-point window method
    si = calculate_saturation_index(conc, cold_f)

    # Build result - store all linear model parameters
    if 'slope1' in linear_result:
        # Piecewise linear model
        linear_params = {
            'slope1': linear_result['slope1'],
            'intercept1': linear_result['intercept1'],
            'slope2': linear_result['slope2'],
            'intercept2': linear_result['intercept2'],
            'breakpoint_conc': linear_result['breakpoint_conc']
        }
    else:
        # Simple linear model (fallback)
        linear_params = {
            'slope': linear_result.get('slope', 0),
            'intercept': linear_result.get('intercept', 0)
        }


    fourpl_params = None
    if fourpl_result['success']:
        fourpl_params = {
            'bottom': fourpl_result['bottom'],
            'top': fourpl_result['top'],
            'ec50': fourpl_result['ec50'],
            'hill': fourpl_result['hill']
        }

    # Determine status based on joint ΔAIC and SI criteria
    # Strategy validated with piecewise linear non-specific model
    status = 'Not detected'
    mode = None
    ec50_app = None
    ec50_app_str = None
    notes_parts = []

    # UPDATED THRESHOLDS (empirically validated with piecewise linear model):
    # ΔAIC thresholds:
    #   ≥ 15: Strong evidence for 4PL over non-specific
    #   ≥ 10: Moderate evidence
    #   < 10: Weak/no evidence
    # SI thresholds (2-point window):
    #   < 0.5: Strong saturation
    #   0.5-1.0: Moderate saturation
    #   ≥ 1.0: Weak/no saturation
    
    delta_aic_strong = 15.0  # Strong evidence threshold (updated from 6.0)
    delta_aic_moderate = 10.0  # Moderate evidence threshold (updated from 3.0)
    si_strong_threshold = 0.5
    si_caution_threshold = 1.0

    if not fourpl_result['success']:
        status = 'Not detected'
        notes_parts.append(f"4PL fit failed: {fourpl_result.get('error', 'Unknown')}")
    elif delta_aic < delta_aic_moderate:
        # Weak AIC evidence - likely non-specific
        status = 'Not detected'
        notes_parts.append(f"Non-specific model fits equally well (ΔAIC={delta_aic:.1f}, SI={si:.3f})")
    else:
        # 4PL is at least moderately better
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

        # Joint ΔAIC + SI determination
        if delta_aic >= delta_aic_strong and si < si_strong_threshold:
            # Strong evidence: high ΔAIC + low SI
            status = 'Detected'
            notes_parts.append(f"Strong saturable signal ({mode})")
        elif delta_aic >= delta_aic_strong:
            # High ΔAIC but moderate/high SI
            status = 'Detected (caution)'
            if si < si_caution_threshold:
                notes_parts.append(f"Strong ΔAIC but moderate SI={si:.3f}, verify saturation plateau")
            else:
                notes_parts.append(f"Warning: High SI={si:.3f} suggests non-saturable binding despite ΔAIC={delta_aic:.1f}")
        elif si < si_strong_threshold:
            # Low SI but moderate ΔAIC
            status = 'Detected (caution)'
            notes_parts.append(f"Good SI={si:.3f} but moderate ΔAIC={delta_aic:.1f}, verify with orthogonal method")
        else:
            # Moderate ΔAIC with moderate/high SI
            status = 'Detected (caution)'
            notes_parts.append(f"Weak evidence: moderate ΔAIC={delta_aic:.1f} and SI={si:.3f}")


    return SFQChannelResult(
        status=status,
        mode=mode,
        ec50_app=ec50_app,
        ec50_app_str=ec50_app_str,
        span=span,
        delta_aic=float(delta_aic) if np.isfinite(delta_aic) else 0.0,
        saturation_index=si,  # 2-point window method
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
    # For plotting on log scale, we generate points across concentration range
    conc_min, conc_max = concentrations.min(), concentrations.max()
    conc_fit = np.logspace(np.log10(conc_min), np.log10(conc_max), 100)

    # Non-specific (piecewise linear) fit curve: F = slope * log10(C) + intercept
    # Generate curve based on whether we have piecewise or simple linear params
    if 'slope1' in channel_result.linear_params:
        # Piecewise linear model
        breakpoint_conc = channel_result.linear_params.get('breakpoint_conc', conc_min)
        log_conc_fit = np.log10(conc_fit)
        
        # Split at breakpoint
        mask_low = conc_fit < breakpoint_conc
        mask_high = conc_fit >= breakpoint_conc
        
        linear_fit_y = np.zeros_like(conc_fit)
        linear_fit_y[mask_low] = (
            channel_result.linear_params['slope1'] * log_conc_fit[mask_low] + 
            channel_result.linear_params['intercept1']
        )
        linear_fit_y[mask_high] = (
            channel_result.linear_params['slope2'] * log_conc_fit[mask_high] + 
            channel_result.linear_params['intercept2']
        )
        linear_fit_y = linear_fit_y.tolist()
    else:
        # Simple linear model (fallback)
        linear_fit_y = linear_c(
            conc_fit,
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
        # Distinguish between different failure modes
        if cr.notes and 'Insufficient signal change' in cr.notes:
            # Truly no significant change
            return f"No significant static fluorescence change detected in F{result.channel_name}."
        elif cr.notes and 'Non-specific model fits equally well' in cr.notes:
            # Significant change but non-specific
            return f"Fluorescence change detected in F{result.channel_name}, but likely due to non-specific binding (inner filter, aggregation, or solubility effects)."
        else:
            # Other failure modes (4PL fit failed, etc.)
            return f"No saturable static fluorescence change detected in F{result.channel_name}."

    mode_str = cr.mode or "change"
    if cr.status == 'Detected':
        return f"Static Fluorescence {mode_str} detected in F{result.channel_name}: EC50_app = {cr.ec50_app_str}"
    else:  # Detected (caution)
        return f"Possible Static Fluorescence {mode_str} in F{result.channel_name}: EC50_app = {cr.ec50_app_str} (interpret with caution)"
