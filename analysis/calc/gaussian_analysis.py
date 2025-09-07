#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gaussian analysis module for peak deconvolution
"""
import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit


def gaussian(x, amp, cen, wid):
    """Single Gaussian peak function"""
    return amp * np.exp(-(x - cen)**2 / (2 * wid**2))


def multi_gaussian(x, *params):
    """
    Sum of multiple Gaussian peaks with a global linear baseline.
    
    Parameters:
        x: x values
        params: flattened list of parameters 
                [amp1, cen1, wid1, ..., ampN, cenN, widN, slope, intercept]
    """
    y_gaussians = np.zeros_like(x)
    num_gaussians = (len(params) - 2) // 3
    
    for i in range(num_gaussians):
        amp = params[i*3]
        cen = params[i*3+1]
        wid = params[i*3+2]
        y_gaussians += gaussian(x, amp, cen, wid)
        
    slope = params[-2]
    intercept = params[-1]
    
    return y_gaussians + slope * x + intercept


def deconvolute_peaks(T, curve, num_peaks=2, temp_range=None):
    """
    Deconvolute a curve into multiple Gaussian peaks
    
    Parameters:
        T (np.ndarray): Temperature array
        curve (np.ndarray): Curve data (e.g., derivative curve)
        num_peaks (int): Number of Gaussian peaks to fit
        temp_range (tuple): Optional temperature range to focus on (min_temp, max_temp)
        
    Returns:
        tuple: (params, peaks_data)
            params: fitted parameters [amp1, cen1, wid1, amp2, cen2, wid2, ...]
            peaks_data: list of dicts with peak information
    """
    # Focus on a specific temperature range if provided
    if temp_range:
        min_temp, max_temp = temp_range
        mask = (T >= min_temp) & (T <= max_temp)
        T_fit = T[mask]
        curve_fit = curve[mask]
    else:
        T_fit = T
        curve_fit = curve

    if len(T_fit) < 5: # Not enough data to find peaks or fit
        return np.array([]), []

    # Refined initial peak selection
    all_candidates = []
    
    # Estimate characteristic spacing for width conversion
    avg_temp_spacing = np.mean(np.diff(T_fit)) if len(T_fit) > 1 else 1.0

    # Find positive peak candidates
    prominence_threshold = 0.05 * np.ptp(curve_fit) if np.ptp(curve_fit) > 1e-6 else 0.05 * np.max(np.abs(curve_fit))
    pos_peak_indices, pos_props = find_peaks(curve_fit, prominence=prominence_threshold, width=(3, None), rel_height=0.5)

    for i, idx in enumerate(pos_peak_indices):
        if 0 <= idx < len(curve_fit):
            fwhm_points = pos_props.get('widths', [5.0])[i] # Default FWHM in points if not found
            fwhm_temp = fwhm_points * avg_temp_spacing
            initial_sigma = fwhm_temp / 2.35482 # Convert FWHM to sigma
            all_candidates.append({
                'index': idx,
                'value': curve_fit[idx],
                'prominence': pos_props['prominences'][i],
                'is_positive': True,
                'initial_sigma': initial_sigma
            })

    # Find negative peak (dip) candidates
    neg_peak_indices, neg_props = find_peaks(-curve_fit, prominence=prominence_threshold, width=(3, None), rel_height=0.5)
    for i, idx in enumerate(neg_peak_indices):
        if 0 <= idx < len(curve_fit):
            fwhm_points = neg_props.get('widths', [5.0])[i]
            fwhm_temp = fwhm_points * avg_temp_spacing
            initial_sigma = fwhm_temp / 2.35482
            all_candidates.append({
                'index': idx,
                'value': curve_fit[idx],
                'prominence': neg_props['prominences'][i],
                'is_positive': False,
                'initial_sigma': initial_sigma
            })

    all_candidates.sort(key=lambda c: c['prominence'], reverse=True)

    selected_peaks_info = []
    seen_indices = set()
    for candidate in all_candidates:
        if len(selected_peaks_info) < num_peaks:
            if candidate['index'] not in seen_indices:
                selected_peaks_info.append({
                    'index': candidate['index'],
                    'value': candidate['value'],
                    'initial_sigma': candidate['initial_sigma']
                })
                seen_indices.add(candidate['index'])
        else:
            break
    
    if len(selected_peaks_info) < num_peaks and len(T_fit) > 0:
        num_needed = num_peaks - len(selected_peaks_info)
        existing_temps = [T_fit[p['index']] for p in selected_peaks_info if 0 <= p['index'] < len(T_fit)]
        potential_temps = np.linspace(T_fit[0], T_fit[-1], num_peaks + 2)[1:-1]

        for _ in range(num_needed):
            best_new_idx = -1
            for temp_guess in potential_temps:
                is_far_enough = all(abs(temp_guess - et) > (T_fit[-1] - T_fit[0]) * 0.05 for et in existing_temps)
                if not is_far_enough: continue
                current_idx = np.argmin(np.abs(T_fit - temp_guess))
                if current_idx in seen_indices: continue
                if current_idx not in seen_indices:
                    best_new_idx = current_idx
                    break
            
            if best_new_idx != -1 and 0 <= best_new_idx < len(T_fit):
                default_sigma_fallback = np.clip((T_fit[-1] - T_fit[0]) / (num_peaks * 6.0 if num_peaks > 0 else 6.0) / 2.35482, 0.5, 3.0)
                selected_peaks_info.append({
                    'index': best_new_idx,
                    'value': curve_fit[best_new_idx],
                    'initial_sigma': default_sigma_fallback 
                })
                seen_indices.add(best_new_idx)
            elif len(T_fit) > 0:
                generic_idx = len(T_fit) // (num_peaks + 1) * (len(selected_peaks_info) + 1)
                generic_idx = np.clip(generic_idx, 0, len(T_fit)-1)
                if generic_idx not in seen_indices:
                    default_sigma_fallback = np.clip((T_fit[-1] - T_fit[0]) / (num_peaks * 6.0 if num_peaks > 0 else 6.0) / 2.35482, 0.5, 3.0)
                    selected_peaks_info.append({
                        'index': generic_idx,
                        'value': curve_fit[generic_idx],
                        'initial_sigma': default_sigma_fallback
                    })
                    seen_indices.add(generic_idx)

    initial_params = []
    if len(T_fit) > 0:
        for peak_info in selected_peaks_info:
            amp = peak_info['value']
            cen = T_fit[peak_info['index']]
            # Use clipped initial_sigma for p0
            clipped_initial_wid = np.clip(peak_info['initial_sigma'], 0.2, 5.0) 
            initial_params.extend([amp, cen, max(0.2, clipped_initial_wid)])

    current_param_count = len(initial_params)
    if current_param_count < 3 * num_peaks:
        num_missing_sets = num_peaks - (current_param_count // 3)
        for _ in range(num_missing_sets):
            amp_guess = np.mean(curve_fit) if len(curve_fit) > 0 else 0
            cen_guess = np.mean(T_fit) if len(T_fit) > 0 else 0
            # Fallback sigma if no peak was found by find_peaks for this slot
            wid_guess = np.clip( (T_fit[-1] - T_fit[0]) / (num_peaks * 10.0 if num_peaks > 0 else 10.0), 0.5, 3.0)
            initial_params.extend([amp_guess, cen_guess, max(0.5, wid_guess)])
    
    initial_params = initial_params[:3*num_peaks]

    # --- Add initial guesses for global linear baseline parameters ---
    slope_guess = 0.0
    intercept_guess = np.min(curve_fit) if len(curve_fit) > 0 else 0.0

    if len(T_fit) > 10: # Need enough points to estimate slope
        # Use first and last 10% of points if available, min 5 points
        num_edge_points = max(5, int(len(T_fit) * 0.1))
        
        # Ensure slices are valid
        if num_edge_points * 2 < len(T_fit):
            y1 = np.mean(curve_fit[:num_edge_points])
            x1 = np.mean(T_fit[:num_edge_points])
            y2 = np.mean(curve_fit[-num_edge_points:])
            x2 = np.mean(T_fit[-num_edge_points:])
            if abs(x2 - x1) > 1e-6: # Avoid division by zero
                slope_guess = (y2 - y1) / (x2 - x1)
            intercept_guess = y1 - slope_guess * x1
        elif len(T_fit) > 0 : # Fallback if not enough points for robust slope guess
             intercept_guess = np.mean(curve_fit[:num_edge_points]) # Use first few points for intercept

    # Append baseline parameters to initial_params
    initial_params.extend([slope_guess, intercept_guess])

    # Set bounds for all parameters
    lower_bounds = []
    upper_bounds = []
    
    # Bounds for Gaussian peaks
    for _ in range(num_peaks):
        # Amplitude bounds - allow negative for dips
        lower_bounds.extend([-np.inf, T_fit[0] if len(T_fit) > 0 else 0, 0.1])
        upper_bounds.extend([np.inf, T_fit[-1] if len(T_fit) > 0 else 100, 10.0])
    
    # Bounds for baseline parameters
    lower_bounds.extend([-np.inf, -np.inf])  # slope, intercept
    upper_bounds.extend([np.inf, np.inf])

    try:
        # Fit the multi-Gaussian function
        popt, pcov = curve_fit(
            multi_gaussian, T_fit, curve_fit, 
            p0=initial_params,
            bounds=(lower_bounds, upper_bounds),
            maxfev=5000
        )
        
        # Extract peak information
        peaks_data = []
        for i in range(num_peaks):
            amp = popt[i*3]
            cen = popt[i*3+1] 
            wid = popt[i*3+2]
            peaks_data.append({
                'amplitude': amp,
                'center': cen,
                'width': wid,
                'area': abs(amp) * wid * np.sqrt(2 * np.pi)  # Gaussian area
            })
        
        # Add baseline parameters
        slope = popt[-2]
        intercept = popt[-1]
        
        return popt, peaks_data, {'slope': slope, 'intercept': intercept}
        
    except Exception as e:
        # Return empty results if fitting fails
        return np.array([]), [], {} 