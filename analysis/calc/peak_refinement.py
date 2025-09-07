#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Peak detection and refinement utilities for nanoDSF analysis
"""
import numpy as np
from scipy.signal import find_peaks, savgol_filter
from scipy.optimize import curve_fit
from .signal_processing import calculate_snr


def calc_tm_polynomial_fit(T, deriv_curve, peak_indices, polynomial_window=3.0):
    """
    Calculates Tm by fitting a 2nd order polynomial to the region around a peak
    in the derivative curve.

    Args:
        T (np.ndarray): Temperature array.
        deriv_curve (np.ndarray): Derivative curve (dF/dT).
        peak_indices (list or np.ndarray): Indices of peaks found by find_peaks.
        polynomial_window (float): Temperature range to include on each side of the peak
                                       for polynomial fitting (in °C). Default ±3°C.

    Returns:
        list: A list of dictionaries, where each dictionary contains:
              'Tm_poly': The Tm determined by the polynomial fit.
              'peak_index': The original index of the peak.
              'coeffs': The polynomial coefficients [a, b, c] for ax^2 + bx + c.
              'r_squared': R-squared value of the fit.
              'area_poly': The area under the polynomial fit within the window.
              'T_window_used': The temperature range used for fitting.
              'deriv_window_used': The derivative values used for fitting.
    """
    tms_poly = []
    if len(T) == 0 or len(deriv_curve) == 0 or len(peak_indices) == 0:
        return tms_poly

    for pk_idx in peak_indices:
        if pk_idx < 0 or pk_idx >= len(T):
            continue
            
        peak_temp = T[pk_idx]
        
        # Define temperature window: peak ± polynomial_window
        temp_min = peak_temp - polynomial_window
        temp_max = peak_temp + polynomial_window
        
        # Find indices within the temperature window
        temp_mask = (T >= temp_min) & (T <= temp_max)
        
        if not np.any(temp_mask):
            continue
        
        # Extract data within the temperature window
        T_window = T[temp_mask]
        deriv_window = deriv_curve[temp_mask]
        
        # Ensure we have enough points for a quadratic fit (at least 3)
        if len(T_window) < 3:
            continue

        try:
            # Fit a 2nd order polynomial: ax^2 + bx + c
            coeffs = np.polyfit(T_window, deriv_window, 2)
            a, b, c = coeffs

            if a == 0: # Not a quadratic, avoid division by zero (should be rare for a peak)
                tm_val = T[pk_idx] # Fallback to find_peaks result
            else:
                # Vertex of parabola: -b / 2a
                tm_val = -b / (2 * a)
            
            # Calculate R-squared for goodness of fit
            poly_func = np.poly1d(coeffs)
            y_pred = poly_func(T_window)
            ss_res = np.sum((deriv_window - y_pred)**2)
            ss_tot = np.sum((deriv_window - np.mean(deriv_window))**2)
            if ss_tot == 0: # Avoid division by zero if all y_values are the same
                r_squared = 1.0 if ss_res < 1e-9 else 0.0 # Perfect fit if residuals are zero
            else:
                r_squared = 1 - (ss_res / ss_tot)

            # Calculate area under the polynomial fit within the window
            # Antiderivative: P(x) = (a/3)x^3 + (b/2)x^2 + cx
            T_start_win, T_end_win = T_window[0], T_window[-1]
            
            val_at_T_end = (a/3)*T_end_win**3 + (b/2)*T_end_win**2 + c*T_end_win
            val_at_T_start = (a/3)*T_start_win**3 + (b/2)*T_start_win**2 + c*T_start_win
            area_poly = val_at_T_end - val_at_T_start

            # Generate fitted curve for visualization (over the fitted temperature range)
            T_fit_curve = np.linspace(temp_min, temp_max, 50)  # 50 points for smooth curve
            poly_func = np.poly1d(coeffs)
            fitted_curve = poly_func(T_fit_curve)

            tms_poly.append({
                'Tm_poly': tm_val,
                'peak_index': pk_idx,
                'coeffs': coeffs.tolist(),
                'r_squared': r_squared,
                'area_poly': area_poly,
                'T_window_used': T_window.tolist(),
                'deriv_window_used': deriv_window.tolist(),
                'window_temp_range': (temp_min, temp_max),
                'window_size_points': len(T_window),
                'T_fit_curve': T_fit_curve.tolist(),  # Temperature points for fitted curve
                'fitted_curve': fitted_curve.tolist()  # Polynomial fitted values
            })
        except (np.linalg.LinAlgError, ValueError) as e:
            # Fallback to original temperature if polynomial fit fails
            tms_poly.append({
                'Tm_poly': T[pk_idx],
                'peak_index': pk_idx,
                'coeffs': None,
                'r_squared': 0.0,
                'area_poly': np.nan,
                'window_temp_range': (temp_min, temp_max),
                'error': str(e)
            })
            
    return tms_poly


def refine_peak_position(T, derivative, initial_idx, search_radius=10):
    """
    Refine peak position using less-smoothed derivative for better precision
    
    Parameters:
        T (np.ndarray): Temperature array
        derivative (np.ndarray): Derivative signal
        initial_idx (int): Initial peak index
        search_radius (int): Search radius for refinement
    
    Returns:
        int: Refined peak index
    """
    if initial_idx < 0 or initial_idx >= len(derivative):
        return initial_idx
    
    # Define search window
    start_search = max(0, initial_idx - search_radius)
    end_search = min(len(derivative), initial_idx + search_radius + 1)
    
    # Find the index with maximum absolute value in the search window
    search_window = derivative[start_search:end_search]
    max_idx_relative = np.argmax(np.abs(search_window))
    refined_idx = start_search + max_idx_relative
    
    return refined_idx


def group_peaks_by_proximity(peaks, temp_threshold=7.0):
    """
    Group peaks by temperature proximity to handle multiple transitions consistently
    
    Parameters:
        peaks (list): List of peak dictionaries with 'temp' and 'snr' keys
        temp_threshold (float): Temperature threshold for grouping (°C)
    
    Returns:
        dict: Grouped peaks with 'low_temp' and 'high_temp' categories
    """
    if not peaks:
        return {'low_temp': [], 'high_temp': []}
    
    # Sort peaks by temperature
    sorted_peaks = sorted(peaks, key=lambda x: x['temp'])
    
    # Find natural break point in temperature distribution
    if len(sorted_peaks) > 1:
        temp_diffs = [sorted_peaks[i+1]['temp'] - sorted_peaks[i]['temp'] 
                     for i in range(len(sorted_peaks)-1)]
        
        # Look for largest gap
        if temp_diffs:
            max_gap_idx = np.argmax(temp_diffs)
            split_temp = (sorted_peaks[max_gap_idx]['temp'] + 
                         sorted_peaks[max_gap_idx+1]['temp']) / 2
        else:
            split_temp = sorted_peaks[0]['temp'] + temp_threshold
    else:
        # Single peak - classify based on temperature range
        peak_temp = sorted_peaks[0]['temp']
        split_temp = 70.0  # Default split at 70°C
    
    # Group peaks
    low_temp_peaks = [p for p in sorted_peaks if p['temp'] < split_temp]
    high_temp_peaks = [p for p in sorted_peaks if p['temp'] >= split_temp]
    
    return {
        'low_temp': low_temp_peaks,
        'high_temp': high_temp_peaks,
        'split_temperature': split_temp
    }


def detect_multiple_peaks(T, derivative, temperature_range=(45, 90), 
                         min_prominence_ratio=0.25, min_temp_separation=2.0,
                         max_peaks=5):
    """
    Detect multiple significant peaks in derivative curve
    
    Parameters:
        T (np.ndarray): Temperature array
        derivative (np.ndarray): Derivative signal
        temperature_range (tuple): Valid temperature range for peaks
        min_prominence_ratio (float): Minimum prominence as fraction of highest peak
        min_temp_separation (float): Minimum temperature separation between peaks
        max_peaks (int): Maximum number of peaks to detect
    
    Returns:
        list: List of detected peaks with temperature, index, SNR, and type
    """
    if len(T) != len(derivative) or len(T) < 10:
        return []
    
    # Apply temperature filtering
    temp_mask = (T >= temperature_range[0]) & (T <= temperature_range[1])
    if not np.any(temp_mask):
        return []
    
    T_filtered = T[temp_mask]
    deriv_filtered = derivative[temp_mask]
    offset = np.where(temp_mask)[0][0]  # Offset for global indexing
    
    # Find positive peaks (actual transitions)
    # Use moderate prominence threshold to catch weak but important signals
    signal_std = np.std(deriv_filtered)
    signal_ptp = np.ptp(deriv_filtered)
    signal_max = np.max(np.abs(deriv_filtered))
    
    # Use 5% of signal range or 2x standard deviation (keeps sensitivity while reducing noise)
    prominence_threshold = max(0.05 * signal_ptp, 2.0 * signal_std) if signal_ptp > 1e-6 else 0.05 * signal_max
    
    pos_peaks, pos_props = find_peaks(deriv_filtered, prominence=prominence_threshold, width=(3, None))
    
    # Find negative peaks (dips)
    neg_peaks, neg_props = find_peaks(-deriv_filtered, prominence=prominence_threshold, width=(3, None))
    
    # Collect all peak candidates
    all_candidates = []
    
    # Process positive peaks
    for i, idx in enumerate(pos_peaks):
        global_idx = idx + offset
        snr = calculate_snr(derivative, global_idx)
        all_candidates.append({
            'temp': T_filtered[idx],
            'idx': global_idx,
            'snr': snr,
            'prominence': pos_props['prominences'][i],
            'type': 'peak'
        })
    
    # Process negative peaks
    for i, idx in enumerate(neg_peaks):
        global_idx = idx + offset
        snr = calculate_snr(derivative, global_idx)
        all_candidates.append({
            'temp': T_filtered[idx],
            'idx': global_idx,
            'snr': snr,
            'prominence': neg_props['prominences'][i],
            'type': 'dip'
        })
    
    if not all_candidates:
        return []
    
    # Sort by SNR (highest first)
    all_candidates.sort(key=lambda x: x['snr'], reverse=True)
    
    # Filter based on prominence and separation
    filtered_peaks = [all_candidates[0]]  # Always keep the highest SNR peak
    top_snr = all_candidates[0]['snr']
    min_snr_threshold = min_prominence_ratio * top_snr
    
    for candidate in all_candidates[1:]:
        # Check SNR threshold
        if candidate['snr'] < min_snr_threshold:
            continue
        
        # Check temperature separation
        is_distinct = True
        for existing_peak in filtered_peaks:
            if abs(candidate['temp'] - existing_peak['temp']) < min_temp_separation:
                is_distinct = False
                break
        
        if is_distinct:
            filtered_peaks.append(candidate)
        
        # Limit number of peaks
        if len(filtered_peaks) >= max_peaks:
            break
    
    return filtered_peaks


def prioritize_peak_types(peaks):
    """
    Prioritize positive peaks over dips for protein unfolding analysis
    
    Parameters:
        peaks (list): List of peak dictionaries
    
    Returns:
        list: Reordered peaks with positive peaks prioritized
    """
    if not peaks:
        return peaks
    
    # Separate positive peaks and dips
    positive_peaks = [p for p in peaks if p['type'] == 'peak']
    negative_peaks = [p for p in peaks if p['type'] == 'dip']
    
    # Sort each type by SNR
    positive_peaks.sort(key=lambda x: x['snr'], reverse=True)
    negative_peaks.sort(key=lambda x: x['snr'], reverse=True)
    
    # If we have good positive peaks, check if we should prefer them over dips
    if positive_peaks and negative_peaks:
        best_positive_snr = positive_peaks[0]['snr']
        best_negative_snr = negative_peaks[0]['snr']
        
        # If positive peak has >= 70% of the SNR of the best dip, prefer it
        if best_positive_snr >= 0.7 * best_negative_snr:
            return positive_peaks + negative_peaks
    
    # Otherwise, maintain original SNR-based ordering
    all_peaks = positive_peaks + negative_peaks
    all_peaks.sort(key=lambda x: x['snr'], reverse=True)
    return all_peaks


def calculate_peak_metrics(T, derivative, peak_idx):
    """
    Calculate comprehensive metrics for a peak
    
    Parameters:
        T (np.ndarray): Temperature array
        derivative (np.ndarray): Derivative signal
        peak_idx (int): Peak index
    
    Returns:
        dict: Peak metrics including SNR, prominence, width, area
    """
    if peak_idx < 0 or peak_idx >= len(derivative):
        return {}
    
    # Basic metrics
    peak_temp = T[peak_idx]
    peak_value = derivative[peak_idx]
    snr = calculate_snr(derivative, peak_idx)
    
    # Find peak width at half maximum
    peak_width, width_bounds = _estimate_peak_width(derivative, peak_idx)
    
    # Calculate area under peak
    if width_bounds is not None:
        start_idx, end_idx = width_bounds
        peak_area = np.trapz(np.abs(derivative[start_idx:end_idx+1]), 
                           T[start_idx:end_idx+1])
    else:
        peak_area = np.nan
    
    # Calculate prominence using scipy method
    try:
        peaks, props = find_peaks(np.abs(derivative), height=0)
        peak_in_list = np.where(peaks == peak_idx)[0]
        if len(peak_in_list) > 0:
            prominence = props.get('prominences', [np.nan])[peak_in_list[0]]
        else:
            prominence = np.nan
    except:
        prominence = np.nan
    
    return {
        'temperature': peak_temp,
        'value': peak_value,
        'snr': snr,
        'width': peak_width,
        'area': peak_area,
        'prominence': prominence,
        'index': peak_idx
    }


def _estimate_peak_width(signal, peak_idx, height_fraction=0.5):
    """
    Estimate peak width at specified height fraction
    
    Parameters:
        signal (np.ndarray): Signal array
        peak_idx (int): Peak index
        height_fraction (float): Height fraction for width measurement
    
    Returns:
        tuple: (width_in_points, (start_idx, end_idx)) or (np.nan, None)
    """
    if peak_idx < 0 or peak_idx >= len(signal):
        return np.nan, None
    
    peak_value = abs(signal[peak_idx])
    threshold = peak_value * height_fraction
    
    # Find left boundary
    left_idx = peak_idx
    while left_idx > 0 and abs(signal[left_idx]) > threshold:
        left_idx -= 1
    
    # Find right boundary
    right_idx = peak_idx
    while right_idx < len(signal) - 1 and abs(signal[right_idx]) > threshold:
        right_idx += 1
    
    width = right_idx - left_idx
    return width, (left_idx, right_idx)


def merge_nearby_peaks(peaks, temperature_threshold=3.0):
    """
    Merge peaks that are very close in temperature
    
    Parameters:
        peaks (list): List of peak dictionaries
        temperature_threshold (float): Temperature threshold for merging
    
    Returns:
        list: Merged peak list
    """
    if len(peaks) <= 1:
        return peaks
    
    # Sort by temperature
    sorted_peaks = sorted(peaks, key=lambda x: x['temp'])
    merged_peaks = [sorted_peaks[0]]
    
    for current_peak in sorted_peaks[1:]:
        last_merged = merged_peaks[-1]
        
        # Check if peaks are close enough to merge
        if abs(current_peak['temp'] - last_merged['temp']) < temperature_threshold:
            # Merge peaks - keep the one with higher SNR
            if current_peak['snr'] > last_merged['snr']:
                merged_peaks[-1] = current_peak
        else:
            # Peaks are far enough apart - keep both
            merged_peaks.append(current_peak)
    
    return merged_peaks 


def rank_peaks_by_importance(peaks, derivative, T):
    """
    Rank peaks by comprehensive importance score combining multiple criteria
    
    Parameters:
        peaks (list): List of peak dictionaries
        derivative (np.ndarray): Derivative signal
        T (np.ndarray): Temperature array
    
    Returns:
        list: Peaks ranked by importance (highest first)
    """
    if not peaks:
        return peaks
    
    # Calculate signal statistics for normalization
    signal_max = np.max(np.abs(derivative))
    signal_std = np.std(derivative)
    signal_mean = np.mean(np.abs(derivative))
    
    # Calculate importance scores for each peak
    for peak in peaks:
        peak_idx = peak['idx']
        peak_temp = peak['temp']
        peak_amp = abs(derivative[peak_idx])
        peak_snr = peak.get('snr', 0)
        peak_prominence = peak.get('prominence', 0)
        
        # 1. Amplitude score (30%): Relative to overall signal strength
        amp_score = peak_amp / signal_max if signal_max > 0 else 0
        
        # 2. SNR score (25%): Signal-to-noise ratio
        snr_score = min(peak_snr / 15.0, 1.0) if peak_snr > 0 else 0
        
        # 3. Prominence score (20%): How much the peak stands out locally
        max_prominence = max([p.get('prominence', 0) for p in peaks])
        prominence_score = peak_prominence / max_prominence if max_prominence > 0 else 0
        
        # 4. Temperature position score (15%): Prefer biologically relevant range
        if 55 <= peak_temp <= 80:
            temp_score = 1.0  # Optimal range for protein unfolding
        elif 50 <= peak_temp <= 85:
            temp_score = 0.9  # Good range
        elif 45 <= peak_temp <= 90:
            temp_score = 0.7  # Acceptable range
        elif 40 <= peak_temp <= 95:
            temp_score = 0.5  # Extended range
        else:
            temp_score = 0.2  # Outside typical range
        
        # 5. Peak type preference (10%): Positive peaks over dips
        type_score = 1.0 if peak.get('type') == 'peak' else 0.7
        
        # Calculate composite importance score (weighted average)
        importance_score = (
            0.30 * amp_score +
            0.25 * snr_score +
            0.20 * prominence_score +
            0.15 * temp_score +
            0.10 * type_score
        )
        
        # Store the score and individual components for debugging
        peak['importance_score'] = importance_score
        peak['score_components'] = {
            'amplitude': amp_score,
            'snr': snr_score,
            'prominence': prominence_score,
            'temperature': temp_score,
            'type': type_score
        }
    
    # Sort by importance score (highest first)
    ranked_peaks = sorted(peaks, key=lambda x: x['importance_score'], reverse=True)
    
    return ranked_peaks 