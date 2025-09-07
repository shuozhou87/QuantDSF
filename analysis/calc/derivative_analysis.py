#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
First Derivative analysis module for nanoDSF Tm calculation
"""
import numpy as np
from .signal_processing import apply_edge_dampening, smooth_signal, smooth_signal_adaptive, interpolate_signal
from .peak_refinement import (detect_multiple_peaks, group_peaks_by_proximity, 
                             prioritize_peak_types, refine_peak_position, merge_nearby_peaks,
                             calc_tm_polynomial_fit, rank_peaks_by_importance)
# Import deconvolution from the working original implementation
from .tm_calc_original import deconvolute_peaks


def calc_tm_derivative(T, F, window_length, return_all_peaks=False, 
                      enable_interpolation=False, use_deconvolution=False, 
                      sg_poly_order=2, multi_peak_detection=False, 
                      use_polynomial_refinement=False, polynomial_window=5):
    """
    Calculate Tm using first derivative method with advanced peak detection
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        window_length (int): Smoothing window length
        return_all_peaks (bool): Whether to return all detected peaks
        enable_interpolation (bool): Whether to use interpolation for higher resolution
        use_deconvolution (bool): Whether to use Gaussian deconvolution
        sg_poly_order (int): Savitzky-Golay polynomial order
        multi_peak_detection (bool): Whether to enable multi-peak detection
        use_polynomial_refinement (bool): Whether to use polynomial fitting for peak refinement
        polynomial_window (int): Half-width of window for polynomial fitting
    
    Returns:
        tuple: (tm_value, smooth_F, smooth_derivative, peak_idx_global, all_potential_peaks, ...)
    """
    if len(T) != len(F) or len(T) < 10:
        return np.nan, np.array([]), np.array([]), -1, []
    
    # Store original data for potential return
    T_orig, F_orig = T.copy(), F.copy()
    
    # Remove NaN values and sort by temperature
    valid_mask = np.isfinite(T) & np.isfinite(F)
    T_clean = T[valid_mask]
    F_clean = F[valid_mask]
    
    if len(T_clean) < 10:
        return np.nan, np.array([]), np.array([]), -1, []
    
    # Sort by temperature
    sort_idx = np.argsort(T_clean)
    T = T_clean[sort_idx]
    F = F_clean[sort_idx]
    
    # Detect high-resolution data and apply appropriate preprocessing
    is_high_resolution = len(T) > 200
    
    # Apply interpolation if requested
    if enable_interpolation:
        T_fine, F_fine = interpolate_signal(T, F, num_points=len(T) * 3)
        T, F = T_fine, F_fine
    
    # Apply standard smoothing 
    smooth_F = smooth_signal(F, window_length, sg_poly_order)
    
    # Calculate derivative
    derivative = np.gradient(smooth_F, T)
    
    # Apply edge dampening to reduce artifacts
    edge_buffer = max(5, len(derivative) // 20)
    dampened_derivative = apply_edge_dampening(derivative, fraction=0.15)
    
    # Use Gaussian deconvolution if requested
    if use_deconvolution:
        return _calc_tm_with_deconvolution(T, F, dampened_derivative, edge_buffer, 
                                         enable_interpolation, T_orig, F_orig,
                                         use_polynomial_refinement, polynomial_window, multi_peak_detection)
    
    # Standard peak detection approach
    if multi_peak_detection or return_all_peaks:
        return _calc_tm_multi_peak(T, dampened_derivative, smooth_F, edge_buffer,
                                 multi_peak_detection, enable_interpolation, T_orig, F_orig,
                                 use_polynomial_refinement, polynomial_window)
    else:
        return _calc_tm_single_peak(T, dampened_derivative, smooth_F, edge_buffer,
                                  enable_interpolation, T_orig, F_orig,
                                  use_polynomial_refinement, polynomial_window)


def _calc_tm_with_deconvolution(T, F, derivative, edge_buffer, enable_interpolation, T_orig, F_orig,
                               use_polynomial_refinement, polynomial_window, multi_peak_detection):
    """Calculate Tm using Gaussian deconvolution method"""
    
    # Use temperature range filtering for biological relevance
    temp_range = (45, 90)  # Typical protein unfolding range
    
    # Determine number of peaks based on multi-peak detection setting
    num_peaks = 2 if multi_peak_detection else 1
    
    # Try deconvolution with appropriate number of peaks
    # Note: tm_calc_original.py returns (params, peaks_data) without baseline_info
    deconv_result = deconvolute_peaks(T, derivative, num_peaks=num_peaks, temp_range=temp_range)
    
    if len(deconv_result) == 2:
        params, peaks_data = deconv_result
        baseline_info = {}
    elif len(deconv_result) == 3:
        params, peaks_data, baseline_info = deconv_result
    else:
        # Unexpected return format
        params, peaks_data, baseline_info = [], [], {}
    
    all_potential_peaks = []
    
    if len(peaks_data) > 0:
        # Extract peak information from deconvolution results
        # The tm_calc_original.py uses 'temp', 'amplitude', etc.
        for i, peak_info in enumerate(peaks_data):
            # Check if using new format ('center') or old format ('temp')
            if 'center' in peak_info:
                center_temp = peak_info['center']
                amplitude = peak_info['amplitude']
                area = peak_info.get('area', 0)
                width = peak_info.get('width', 1.0)
            elif 'temp' in peak_info:
                # Old format compatibility
                center_temp = peak_info['temp']
                amplitude = peak_info['amplitude']
                area = peak_info.get('area', 0)
                width = peak_info.get('width', 1.0)
            else:
                continue  # Skip malformed peak info
            
            # Find corresponding index in temperature array
            peak_idx = np.argmin(np.abs(T - center_temp))
            
            # Create peak entry with standardized format
            peak_entry = {
                'temp': center_temp,
                'idx': peak_idx,
                'amplitude': amplitude,
                'width': width,
                'area': area,
                'type': 'deconvoluted',
                'deconvolved': True,
                'peak_number': i + 1,
                'snr': peak_info.get('snr', 5.0)  # Default SNR if not calculated
            }
            all_potential_peaks.append(peak_entry)
        
        # Primary Tm is the peak with largest absolute amplitude
        primary_peak = max(all_potential_peaks, key=lambda x: abs(x['amplitude']))
        tm_value = primary_peak['temp']
        peak_idx_global = primary_peak['idx']
        
        # Add fitted curve data for plotting if we have the parameters
        if len(params) > 0:
            # Generate the composite fitted curve using the multi_gaussian function
            from .tm_calc_original import multi_gaussian
            fitted_curve = multi_gaussian(T, *params)
            
            # Attach the fitted curve to all peaks for plotting
            for peak in all_potential_peaks:
                peak['fitted_curve'] = fitted_curve
        
        # For single-peak mode, filter the additional peaks to only return the primary peak
        if not multi_peak_detection:
            # Keep only the primary peak in the results
            all_potential_peaks = [primary_peak]
    else:
        # Fallback to standard method if deconvolution fails
        return _calc_tm_single_peak(T, derivative, F, edge_buffer, enable_interpolation, T_orig, F_orig, use_polynomial_refinement, polynomial_window)
    
    # Return results
    if enable_interpolation:
        return tm_value, F, derivative, peak_idx_global, all_potential_peaks, T, T_orig, F_orig
    else:
        return tm_value, F, derivative, peak_idx_global, all_potential_peaks


def _calc_tm_multi_peak(T, derivative, smooth_F, edge_buffer, multi_peak_detection, 
                       enable_interpolation, T_orig, F_orig, use_polynomial_refinement, polynomial_window):
    """Calculate Tm with multi-peak detection capability"""
    
    # Detect multiple peaks
    detected_peaks = detect_multiple_peaks(
        T, derivative,
        temperature_range=(45, 90),
        min_prominence_ratio=0.15,  # Keep reasonable threshold for sensitivity
        min_temp_separation=2.0,
        max_peaks=10  # Detect more peaks initially
    )
    
    if not detected_peaks:
        return np.nan, smooth_F, derivative, -1, []
    
    # Rank all peaks by importance
    ranked_peaks = rank_peaks_by_importance(detected_peaks, derivative, T)
    
    # Prioritize positive peaks over dips (additional filtering)
    prioritized_peaks = prioritize_peak_types(ranked_peaks)
    
    # Merge nearby peaks to avoid duplicates
    merged_peaks = merge_nearby_peaks(prioritized_peaks, temperature_threshold=3.0)
    
    # Group peaks by temperature for consistent assignment
    if multi_peak_detection and len(merged_peaks) > 1:
        grouped_peaks = group_peaks_by_proximity(merged_peaks, temp_threshold=7.0)
        
        # Select primary and secondary peaks
        all_potential_peaks = []
        
        # Low temperature peaks
        if grouped_peaks['low_temp']:
            best_low = max(grouped_peaks['low_temp'], key=lambda x: x['snr'])
            all_potential_peaks.append(best_low)
        
        # High temperature peaks  
        if grouped_peaks['high_temp']:
            best_high = max(grouped_peaks['high_temp'], key=lambda x: x['snr'])
            all_potential_peaks.append(best_high)
        
        # Primary Tm is the peak with highest SNR overall
        primary_peak = max(merged_peaks, key=lambda x: x['snr'])
        
    else:
        # Single peak mode - just use the best peak
        primary_peak = merged_peaks[0]
        all_potential_peaks = merged_peaks[:1]  # Keep only the primary peak
    
    # Refine peak positions
    refined_peaks = []
    for peak in all_potential_peaks:
        refined_idx = refine_peak_position(T, derivative, peak['idx'] - edge_buffer)
        if 0 <= refined_idx < len(T):
            refined_peak = peak.copy()
            refined_peak['idx'] = refined_idx
            refined_peak['temp'] = T[refined_idx]
            refined_peaks.append(refined_peak)
    
    # Set primary Tm
    if refined_peaks:
        # Find the refined version of our primary peak
        primary_refined = None
        for peak in refined_peaks:
            if abs(peak['temp'] - primary_peak['temp']) < 3.0:  # Within 3°C
                primary_refined = peak
                break
        
        if primary_refined:
            tm_value = primary_refined['temp']
            peak_idx_global = primary_refined['idx']
        else:
            tm_value = primary_peak['temp']
            peak_idx_global = primary_peak['idx']
    else:
        tm_value = primary_peak['temp']
        peak_idx_global = primary_peak['idx']
    
    # Apply polynomial refinement if requested
    if use_polynomial_refinement and not np.isnan(tm_value):
        peak_indices_for_poly = [peak['idx'] for peak in refined_peaks if 'idx' in peak]
        if not peak_indices_for_poly:  # Fallback to primary peak
            peak_indices_for_poly = [peak_idx_global]
        
        poly_results = calc_tm_polynomial_fit(T, derivative, peak_indices_for_poly, polynomial_window)
        if poly_results:
            primary_poly = poly_results[0]  # Use the first (primary) result
            tm_poly = primary_poly.get('Tm_poly', tm_value)
            
            # Update Tm value and add polynomial info to peak data
            if not np.isnan(tm_poly):
                tm_value = tm_poly
                # Update peak information with polynomial results
                for i, peak in enumerate(refined_peaks):
                    if i < len(poly_results):
                        peak['Tm_poly'] = poly_results[i].get('Tm_poly', peak['temp'])
                        peak['poly_coeffs'] = poly_results[i].get('coeffs', None)
                        peak['poly_r_squared'] = poly_results[i].get('r_squared', np.nan)
                        peak['poly_area'] = poly_results[i].get('area_poly', np.nan)
                        # Add fitted curve data for plotting
                        peak['T_fit_curve'] = poly_results[i].get('T_fit_curve', [])
                        peak['fitted_curve'] = poly_results[i].get('fitted_curve', [])
                        peak['polynomial_fitted'] = True
    
    # Return results
    if enable_interpolation:
        return tm_value, smooth_F, derivative, peak_idx_global, refined_peaks, T, T_orig, F_orig
    else:
        return tm_value, smooth_F, derivative, peak_idx_global, refined_peaks


def _calc_tm_single_peak(T, derivative, smooth_F, edge_buffer, enable_interpolation, T_orig, F_orig, use_polynomial_refinement, polynomial_window):
    """Calculate Tm with enhanced peak detection that finds the most important peak"""
    
    # Always detect multiple peaks to find the most important one
    detected_peaks = detect_multiple_peaks(
        T, derivative,
        temperature_range=(45, 90),
        min_prominence_ratio=0.15,  # Keep reasonable threshold to catch weak but important signals
        min_temp_separation=3.0,
        max_peaks=10  # Detect more peaks to ensure we don't miss any
    )
    
    if not detected_peaks:
        # Try with more relaxed criteria if nothing found
        detected_peaks = detect_multiple_peaks(
            T, derivative,
            temperature_range=(40, 95),  # Slightly wider range
            min_prominence_ratio=0.1,   # More relaxed
            min_temp_separation=2.0,
            max_peaks=10
        )
    
    if not detected_peaks:
        return np.nan, smooth_F, derivative, -1, []
    
    # Rank all peaks by comprehensive importance score
    ranked_peaks = rank_peaks_by_importance(detected_peaks, derivative, T)
    
    # Select the highest-ranked peak as primary
    best_peak = ranked_peaks[0]
    
    # Refine peak position using standard refinement
    refined_idx = refine_peak_position(T, derivative, best_peak['idx'] - edge_buffer)
    
    if 0 <= refined_idx < len(T):
        tm_value = T[refined_idx]
        peak_idx_global = refined_idx
        # Update the peak info with refined position
        best_peak['idx'] = refined_idx
        best_peak['temp'] = tm_value
    else:
        tm_value = best_peak['temp']
        peak_idx_global = best_peak['idx']
    
    # Apply polynomial refinement if requested
    if use_polynomial_refinement and not np.isnan(tm_value):
        poly_results = calc_tm_polynomial_fit(T, derivative, [peak_idx_global], polynomial_window)
        if poly_results:
            primary_poly = poly_results[0]
            tm_poly = primary_poly.get('Tm_poly', tm_value)
            
            if not np.isnan(tm_poly):
                tm_value = tm_poly
                # Add polynomial information to the peak
                best_peak['Tm_poly'] = tm_poly
                best_peak['poly_coeffs'] = primary_poly.get('coeffs', None)
                best_peak['poly_r_squared'] = primary_poly.get('r_squared', np.nan)
                best_peak['poly_area'] = primary_poly.get('area_poly', np.nan)
                # Add fitted curve data for plotting
                best_peak['T_fit_curve'] = primary_poly.get('T_fit_curve', [])
                best_peak['fitted_curve'] = primary_poly.get('fitted_curve', [])
                best_peak['polynomial_fitted'] = True
    
    # Return results with the ranked peak list (all peaks available for multi-peak analysis)
    if enable_interpolation:
        return tm_value, smooth_F, derivative, peak_idx_global, ranked_peaks, T, T_orig, F_orig
    else:
        return tm_value, smooth_F, derivative, peak_idx_global, ranked_peaks


def validate_derivative_result(T, derivative, tm_value, peak_idx):
    """
    Validate the derivative analysis result
    
    Parameters:
        T (np.ndarray): Temperature array
        derivative (np.ndarray): Derivative curve
        tm_value (float): Calculated Tm
        peak_idx (int): Peak index
    
    Returns:
        dict: Validation results with quality metrics
    """
    if np.isnan(tm_value) or peak_idx < 0 or peak_idx >= len(T):
        return {
            'valid': False,
            'quality_score': 0.0,
            'warnings': ['Invalid Tm or peak index']
        }
    
    warnings = []
    quality_factors = []
    
    # Check temperature range
    if tm_value < 30 or tm_value > 100:
        warnings.append(f'Tm ({tm_value:.1f}°C) outside typical range (30-100°C)')
        quality_factors.append(0.3)
    else:
        quality_factors.append(1.0)
    
    # Check derivative signal strength
    peak_value = abs(derivative[peak_idx])
    derivative_std = np.std(derivative)
    
    if derivative_std > 0:
        signal_strength = peak_value / derivative_std
        if signal_strength < 2.0:
            warnings.append('Low signal-to-noise ratio in derivative')
            quality_factors.append(0.5)
        else:
            quality_factors.append(min(signal_strength / 5.0, 1.0))
    else:
        warnings.append('Zero derivative variation')
        quality_factors.append(0.0)
    
    # Check for multiple competing peaks
    competing_peaks = detect_multiple_peaks(T, derivative, max_peaks=3)
    if len(competing_peaks) > 1:
        # Check if other peaks are much weaker
        main_peak_snr = competing_peaks[0]['snr']
        secondary_peak_snr = competing_peaks[1]['snr']
        
        if secondary_peak_snr > 0.7 * main_peak_snr:
            warnings.append('Multiple strong peaks detected - consider multi-peak analysis')
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.9)
    else:
        quality_factors.append(1.0)
    
    # Calculate overall quality score
    overall_quality = np.mean(quality_factors)
    
    return {
        'valid': len([w for w in warnings if 'Invalid' in w]) == 0,
        'quality_score': overall_quality,
        'warnings': warnings,
        'signal_strength': signal_strength if 'signal_strength' in locals() else 0.0,
        'num_competing_peaks': len(competing_peaks) if 'competing_peaks' in locals() else 0
    } 