#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AUC-based Tm calculation module for nanoDSF analysis
Area Under the Curve method for determining melting temperature
"""
import numpy as np
from scipy import integrate
from scipy.interpolate import interp1d
from .signal_processing import smooth_signal

# Handle scipy compatibility - cumtrapz was renamed to cumulative_trapezoid in scipy >= 1.14.0
try:
    from scipy.integrate import cumulative_trapezoid as cumtrapz
except ImportError:
    from scipy.integrate import cumtrapz


def calc_tm_auc(T, F, method='derivative', baseline_correction=True, 
                smoothing_window=11, interpolation_factor=3):
    """
    Calculate Tm using Area Under the Curve (AUC) method
    
    The AUC method determines Tm as the temperature where 50% of the total 
    derivative area (integral) has been reached. This provides a robust measure
    that is less sensitive to noise compared to peak-finding methods.
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        method (str): Analysis method - only 'derivative' is supported
        baseline_correction (bool): Whether to apply baseline correction
        smoothing_window (int): Window size for smoothing (must be odd)
        interpolation_factor (int): Factor for interpolation to increase resolution
    
    Returns:
        dict: Results containing Tm_AUC, total_area, cumulative_areas, and quality metrics
    """
    if len(T) != len(F) or len(T) < 10:
        return {
            'success': False,
            'Tm_AUC': np.nan,
            'total_area': np.nan,
            'area_50_percent': np.nan,
            'quality_score': 0.0,
            'error': 'Insufficient data points'
        }
    
    try:
        # Remove NaN values
        valid_mask = np.isfinite(T) & np.isfinite(F)
        T_clean = T[valid_mask]
        F_clean = F[valid_mask]
        
        if len(T_clean) < 10:
            return {
                'success': False,
                'Tm_AUC': np.nan,
                'total_area': np.nan,
                'area_50_percent': np.nan,
                'quality_score': 0.0,
                'error': 'Too many invalid data points'
            }
        
        # Sort by temperature if not already sorted
        sort_idx = np.argsort(T_clean)
        T_sorted = T_clean[sort_idx]
        F_sorted = F_clean[sort_idx]
        
        # Only derivative method is supported now
        if method == 'derivative':
            return _calc_tm_auc_derivative(T_sorted, F_sorted, baseline_correction, 
                                         smoothing_window, interpolation_factor)
        else:
            return {
                'success': False,
                'Tm_AUC': np.nan,
                'total_area': np.nan,
                'area_50_percent': np.nan,
                'quality_score': 0.0,
                'error': f'Only derivative method is supported. Requested: {method}'
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


def _calc_tm_auc_derivative(T, F, baseline_correction, smoothing_window, interpolation_factor):
    """Calculate AUC-based Tm using derivative method"""
    
    # Apply smoothing
    F_smooth = smooth_signal(F, smoothing_window)
    
    # Calculate derivative
    dF_dT = np.gradient(F_smooth, T)
    
    # Apply baseline correction if requested
    if baseline_correction:
        dF_dT = _apply_baseline_correction(T, dF_dT)
    
    # Interpolate for higher resolution
    if interpolation_factor > 1:
        T_interp, dF_dT_interp = _interpolate_data(T, dF_dT, interpolation_factor)
    else:
        T_interp, dF_dT_interp = T, dF_dT
    
    # Calculate cumulative area (integral of derivative)
    cumulative_area = cumtrapz(np.abs(dF_dT_interp), T_interp, initial=0)
    total_area = cumulative_area[-1]
    
    if total_area == 0:
        return {
            'success': False,
            'Tm_AUC': np.nan,
            'total_area': 0.0,
            'area_50_percent': 0.0,
            'quality_score': 0.0,
            'error': 'Zero total area'
        }
    
    # Find temperature where 50% of area is reached
    target_area = total_area * 0.5
    idx_50 = np.argmin(np.abs(cumulative_area - target_area))
    Tm_AUC = T_interp[idx_50]
    
    # Calculate quality metrics
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


def _apply_baseline_correction(T, derivative):
    """Apply baseline correction to derivative curve"""
    # Use linear baseline correction
    # Fit linear trend to first and last 20% of data
    n_points = len(T)
    edge_points = max(5, n_points // 5)
    
    # Combine edge regions for baseline estimation
    T_baseline = np.concatenate([T[:edge_points], T[-edge_points:]])
    deriv_baseline = np.concatenate([derivative[:edge_points], derivative[-edge_points:]])
    
    # Fit linear baseline
    if len(T_baseline) > 1:
        coeffs = np.polyfit(T_baseline, deriv_baseline, 1)
        baseline = np.polyval(coeffs, T)
        return derivative - baseline
    else:
        return derivative


def _apply_baseline_correction_direct(T, fluorescence):
    """Apply baseline correction to fluorescence curve using polynomial detrending"""
    # Use quadratic detrending for fluorescence data
    try:
        # Fit quadratic baseline
        coeffs = np.polyfit(T, fluorescence, 2)
        baseline = np.polyval(coeffs, T)
        
        # Remove baseline trend but preserve the transition shape
        F_detrended = fluorescence - baseline
        
        # Normalize to positive values for area calculation
        F_detrended = F_detrended - F_detrended.min()
        
        return F_detrended
    except:
        # Fallback to simple linear detrending
        coeffs = np.polyfit(T, fluorescence, 1)
        baseline = np.polyval(coeffs, T)
        F_detrended = fluorescence - baseline
        F_detrended = F_detrended - F_detrended.min()
        return F_detrended


def _interpolate_data(T, signal, factor):
    """Interpolate data to higher resolution"""
    f_interp = interp1d(T, signal, kind='cubic', bounds_error=False, fill_value='extrapolate')
    T_new = np.linspace(T.min(), T.max(), len(T) * factor)
    signal_new = f_interp(T_new)
    return T_new, signal_new


def _calculate_auc_quality(T, derivative, cumulative_area, total_area):
    """Calculate quality score for derivative-based AUC method"""
    # Quality metrics:
    # 1. Signal-to-noise ratio of derivative
    # 2. Monotonicity of cumulative area
    # 3. Steepness of transition
    
    quality_factors = []
    
    # 1. SNR of derivative signal
    signal_std = np.std(derivative)
    noise_level = np.std(derivative[:len(derivative)//10])  # Noise from first 10%
    if noise_level > 0:
        snr = signal_std / noise_level
        quality_factors.append(min(snr / 10.0, 1.0))  # Normalize to [0,1]
    else:
        quality_factors.append(1.0)
    
    # 2. Monotonicity of cumulative area (should always increase)
    area_diff = np.diff(cumulative_area)
    monotonic_fraction = np.sum(area_diff >= 0) / len(area_diff)
    quality_factors.append(monotonic_fraction)
    
    # 3. Transition steepness (derivative peak prominence)
    if len(derivative) > 10:
        derivative_range = np.ptp(derivative)  # peak-to-peak range
        derivative_mean = np.mean(np.abs(derivative))
        if derivative_mean > 0:
            steepness = derivative_range / derivative_mean
            quality_factors.append(min(steepness / 5.0, 1.0))  # Normalize
        else:
            quality_factors.append(0.5)
    else:
        quality_factors.append(0.5)
    
    # Overall quality as weighted average
    weights = [0.4, 0.3, 0.3]  # SNR, monotonicity, steepness
    quality_score = np.average(quality_factors, weights=weights)
    
    return np.clip(quality_score, 0.0, 1.0)


def calc_multi_tm_auc(T, F, num_transitions=2, method='derivative', **kwargs):
    """
    Calculate multiple Tm values using AUC method for proteins with multiple transitions
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array  
        num_transitions (int): Expected number of transitions
        method (str): Analysis method - 'derivative' or 'direct'
        **kwargs: Additional parameters for calc_tm_auc
    
    Returns:
        dict: Results containing multiple Tm_AUC values and transition information
    """
    # First calculate overall AUC
    overall_result = calc_tm_auc(T, F, method=method, **kwargs)
    
    if not overall_result['success']:
        return overall_result
    
    # Divide the cumulative area into equal segments for multiple transitions
    cumulative_area = overall_result['cumulative_area']
    T_range = overall_result['temperature_range']
    total_area = overall_result['total_area']
    
    transition_temps = []
    transition_areas = []
    
    for i in range(1, num_transitions + 1):
        fraction = i / (num_transitions + 1)
        target_area = total_area * fraction
        idx = np.argmin(np.abs(cumulative_area - target_area))
        
        transition_temps.append(T_range[idx])
        transition_areas.append(target_area)
    
    # Add the main Tm (50% area) if not already included
    main_tm = overall_result['Tm_AUC']
    if main_tm not in transition_temps:
        transition_temps.append(main_tm)
        transition_areas.append(overall_result['area_50_percent'])
    
    # Sort by temperature
    sorted_indices = np.argsort(transition_temps)
    transition_temps = [transition_temps[i] for i in sorted_indices]
    transition_areas = [transition_areas[i] for i in sorted_indices]
    
    overall_result.update({
        'transition_temperatures': transition_temps,
        'transition_areas': transition_areas,
        'num_transitions': len(transition_temps),
        'multi_transition': True
    })
    
    return overall_result


def compare_auc_methods(T, F, **kwargs):
    """
    Compare derivative and direct AUC methods side by side
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        **kwargs: Additional parameters for calc_tm_auc
    
    Returns:
        dict: Comparison results from both methods
    """
    # Calculate using derivative method
    deriv_result = calc_tm_auc(T, F, method='derivative', **kwargs)
    
    # Calculate using direct method
    direct_result = calc_tm_auc(T, F, method='direct', **kwargs)
    
    # Calculate difference and recommend best method
    if deriv_result['success'] and direct_result['success']:
        tm_difference = abs(deriv_result['Tm_AUC'] - direct_result['Tm_AUC'])
        
        # Recommend method based on quality scores
        if deriv_result['quality_score'] > direct_result['quality_score']:
            recommended = 'derivative'
        elif direct_result['quality_score'] > deriv_result['quality_score']:
            recommended = 'direct'
        else:
            recommended = 'derivative'  # Default to derivative method
    else:
        tm_difference = np.nan
        if deriv_result['success']:
            recommended = 'derivative'
        elif direct_result['success']:
            recommended = 'direct'
        else:
            recommended = None
    
    return {
        'derivative_method': deriv_result,
        'direct_method': direct_result,
        'tm_difference': tm_difference,
        'recommended_method': recommended,
        'comparison_success': deriv_result['success'] or direct_result['success']
    } 