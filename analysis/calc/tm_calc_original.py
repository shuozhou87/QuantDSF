#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TM calculation module
"""
import numpy as np
from scipy.signal import savgol_filter, find_peaks
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit
from scipy import stats

# Add Gaussian functions for peak deconvolution
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

    # Append to initial_params if it was already populated by Gaussian guesses
    # If initial_params is empty (e.g. selected_peaks_info was empty and num_peaks was 0),
    # this means we are only fitting a baseline, which is unusual but let's handle it.
    
    # Reconstruct initial_params for Gaussians first
    gauss_initial_params = []
    if len(T_fit) > 0:
        for peak_info in selected_peaks_info: # selected_peaks_info might be empty if num_peaks=0
            amp = peak_info['value']
            cen = T_fit[peak_info['index']]
            clipped_initial_wid = np.clip(peak_info['initial_sigma'], 0.2, 5.0) 
            gauss_initial_params.extend([amp, cen, max(0.2, clipped_initial_wid)])

    # Fill remaining Gaussian params if num_peaks > len(selected_peaks_info)
    num_gauss_params_needed = num_peaks * 3
    if len(gauss_initial_params) < num_gauss_params_needed:
        num_missing_gauss_sets = (num_gauss_params_needed - len(gauss_initial_params)) // 3
        for _ in range(num_missing_gauss_sets):
            amp_guess_fallback = np.mean(curve_fit) if len(curve_fit) > 0 else 0
            cen_guess_fallback = np.mean(T_fit) if len(T_fit) > 0 else 0
            wid_guess_fallback = np.clip((T_fit[-1] - T_fit[0]) / (num_peaks * 10.0 if num_peaks > 0 else 10.0), 0.5, 3.0)
            gauss_initial_params.extend([amp_guess_fallback, cen_guess_fallback, max(0.5, wid_guess_fallback)])
    
    initial_params = gauss_initial_params[:num_gauss_params_needed] # Ensure correct number of Gaussian params
    initial_params.extend([slope_guess, intercept_guess])

    # --- Set bounds, including for baseline parameters ---
    lower_bounds = []
    upper_bounds = []
    
    for i in range(num_peaks):
        idx_p0_wid = i*3 + 2
        p0_wid_for_bounds = 1.0 
        if idx_p0_wid < len(initial_params): # Check gauss_initial_params actually
             p0_wid_for_bounds = gauss_initial_params[idx_p0_wid] # Use sigma from Gaussian part for its bound
        else: # Should not happen if selected_peaks_info or fallback loop worked
            if len(T_fit) > 0:
                p0_wid_for_bounds = np.clip( (T_fit[-1] - T_fit[0]) / (num_peaks * 10.0 if num_peaks > 0 else 10.0), 0.5, 3.0)
            # else p0_wid_for_bounds remains 1.0

        # Adaptive upper bound for width (sigma)
        adaptive_upper_wid = min(max(0.5, p0_wid_for_bounds * 1.5), 7.0)

        min_T_bound = T_fit[0] if len(T_fit)>0 else 0
        max_T_bound = T_fit[-1] if len(T_fit)>0 else 100
        if min_T_bound >= max_T_bound : max_T_bound = min_T_bound +1 # Ensure valid range if T_fit is tiny

        lower_bounds.extend([-np.inf, min_T_bound, 0.1])  # Min sigma 0.1 °C
        upper_bounds.extend([np.inf, max_T_bound, adaptive_upper_wid])

    # Bounds for baseline
    # Slope: allow it to vary reasonably, e.g., max change of 0.5 units of dF/dT per °C
    # Intercept: within a wider range around the data's min/max
    data_range = np.ptp(curve_fit) if len(curve_fit) > 1 else 1.0
    temp_span = np.ptp(T_fit) if len(T_fit) > 1 else 50.0 # Typical span
    
    # Slope bounds: limit to prevent extreme slopes, e.g. max change of `data_range` over `temp_span/2`
    max_abs_slope = (data_range / (temp_span / 4.0)) if temp_span > 1e-1 else 1.0 
    max_abs_slope = min(max_abs_slope, 1.0) # Cap max slope magnitude
    
    lower_bounds.extend([-max_abs_slope, np.min(curve_fit) - data_range if len(curve_fit)>0 else -10]) 
    upper_bounds.extend([max_abs_slope, np.max(curve_fit) + data_range if len(curve_fit)>0 else 10])
    
    if not initial_params or len(initial_params) != num_peaks * 3 + 2: # Cannot fit if params are not correctly structured
        # This condition might need refinement based on how initial_params is built
        # If num_peaks is 0, initial_params should be [slope_guess, intercept_guess] -> len 2
        # So, if num_peaks > 0, len should be num_peaks * 3 + 2
        # If num_peaks == 0, len should be 2
        expected_len = num_peaks * 3 + 2 if num_peaks > 0 else 2
        if not initial_params or len(initial_params) != expected_len:
             print(f"Debug: deconvolute_peaks - initial_params structure error. Expected len {expected_len}, got {len(initial_params)}. Params: {initial_params}")
             return np.array([]), []

    try:
        params, _ = curve_fit(
            multi_gaussian, 
            T_fit, 
            curve_fit, 
            p0=initial_params,
            bounds=(lower_bounds, upper_bounds),
            maxfev=10000 # Increased maxfev
        )
    except Exception as e:
        print(f"Error during curve_fit in deconvolute_peaks: {e}")
        print(f"Initial params: {initial_params}")
        print(f"Lower bounds: {lower_bounds}")
        print(f"Upper bounds: {upper_bounds}")
        params = np.array(initial_params) # Fallback to initial params
    
    # Extract individual peak information (Gaussians only)
    peaks_data = []
    for i in range(num_peaks): # Iterate only for num_peaks
        amp = params[i*3]
        cen = params[i*3+1]
        wid = params[i*3+2]
        
        height = gaussian(cen, amp, cen, wid)
        area = amp * wid * np.sqrt(2 * np.pi)
        noise_region = curve_fit[(T_fit < cen - 2*wid) | (T_fit > cen + 2*wid)]
        if len(noise_region) > 5:
            noise = np.std(noise_region)
            snr = height / noise if noise > 0 else 0
        else:
            snr = 0
        peak_info = {
            'temp': cen, 'amplitude': amp, 'width': wid,
            'height': height, 'area': area, 'snr': snr, 'type': 'peak'
        }
        peaks_data.append(peak_info)
    
    peaks_data.sort(key=lambda x: x['temp'])
    
    # Return all fitted parameters (Gaussians + baseline) and data for Gaussian components
    return params, peaks_data


def boltzmann_exp(T, A_N, alpha, D_N, A_D, beta, D_D, Tm, k):
    """
    Boltzmann equation for two-state model
    
    Parameters:
        T (np.ndarray): Temperature array
        A_N (float): Native state amplitude
        alpha (float): Native state slope
        D_N (float): Native state offset
        A_D (float): Denatured state amplitude
        beta (float): Denatured state slope
        D_D (float): Denatured state offset
        Tm (float): Melting temperature
        k (float): Slope factor
        
    Returns:
        np.ndarray: Fitted fluorescence values
    """
    # Add numerical stability by clipping temperature range
    T_clip = np.clip(T, T.min(), T.max())
    
    # Calculate native and denatured state baselines
    F_N = A_N * np.exp(-alpha * T_clip) + D_N  # Native state: first-order exponential decay
    F_D = A_D * np.exp(-beta * T_clip) + D_D   # Denatured state: first-order exponential decay
    
    # Add numerical stability to the transition term
    transition = 1 / (1 + np.exp((Tm - T_clip) / k))
    
    # Calculate total fluorescence
    return F_N + (F_D - F_N) * transition


def apply_edge_dampening(signal, fraction=0.15):
    """
    Apply a dampening effect to the edges of a signal
    
    Parameters:
        signal (np.ndarray): Input signal array
        fraction (float): Fraction of signal length to dampen on each side
        
    Returns:
        np.ndarray: Signal with dampened edges
    """
    n = len(signal)
    dampen_points = int(n * fraction)
    
    if dampen_points < 2:
        return signal.copy()
    
    damped = signal.copy()
    
    # Create dampening windows (cosine taper)
    left_window = 0.5 * (1 - np.cos(np.pi * np.arange(dampen_points) / dampen_points))
    right_window = left_window[::-1]
    
    # Apply dampening to the edges
    damped[:dampen_points] *= left_window
    damped[-dampen_points:] *= right_window
    
    return damped


def calculate_snr(signal, peak_idx, window_size=10):
    """
    Calculate SNR (Signal-to-Noise Ratio) for a peak or dip
    
    Parameters:
        signal (np.ndarray): Signal array
        peak_idx (int): Index of the peak or dip
        window_size (int): Window size for noise calculation
        
    Returns:
        float: SNR value
    """
    # Get the signal value at the peak/dip
    signal_value = signal[peak_idx]
    
    # Extract regions before and after the peak (avoiding the peak area)
    n = len(signal)
    pre_start = max(0, peak_idx - 3*window_size)
    pre_end = max(0, peak_idx - window_size)
    post_start = min(n, peak_idx + window_size)
    post_end = min(n, peak_idx + 3*window_size)
    
    # Extract baseline regions for noise calculation
    baseline_regions = []
    
    if pre_end - pre_start >= 5:
        baseline_regions.append(signal[pre_start:pre_end])
    
    if post_end - post_start >= 5:
        baseline_regions.append(signal[post_start:post_end])
        
    # If we don't have enough points in either region, use more of the signal
    if len(baseline_regions) == 0 or sum(len(r) for r in baseline_regions) < 10:
        left_half = signal[:max(1, peak_idx-5)]
        right_half = signal[min(n, peak_idx+5):]
        
        if len(left_half) > 5:
            baseline_regions.append(left_half)
        if len(right_half) > 5:
            baseline_regions.append(right_half)
    
    # Combine baseline regions
    if baseline_regions:
        baseline = np.concatenate(baseline_regions)
    else:
        # Fallback if we can't get a good baseline
        baseline = np.concatenate([signal[:peak_idx//2], signal[peak_idx+peak_idx//2:]])
    
    # Calculate noise as standard deviation of baseline
    noise = np.std(baseline)
    if noise == 0:
        noise = np.finfo(float).eps  # Avoid division by zero
    
    # Calculate baseline mean
    baseline_mean = np.mean(baseline)
    
    # Calculate SNR as |signal - baseline_mean| / noise
    snr = abs(signal_value - baseline_mean) / noise
    
    return snr


def calc_tm_derivative(T, F, window_length, return_all_peaks=False, enable_interpolation=False, use_deconvolution=False, sg_poly_order=2):
    """
    Calculate TM using first derivative method with SNR-based peak detection
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        window_length (int): Savitzky-Golay filter window length
        return_all_peaks (bool): Whether to return all potential peaks (for multi-peak detection)
        enable_interpolation (bool): Whether to use interpolation for smoother curves
        use_deconvolution (bool): Whether to use Gaussian deconvolution for peak detection
        sg_poly_order (int): Polynomial order for Savitzky-Golay filter (default 2)
        
    Returns:
        tuple: (TM value, smoothed fluorescence, derivative curve, peak index, [additional_peaks])
               where additional_peaks is a list of dicts with 'temp', 'idx', 'snr', and other properties
    """
    # Validation: ensure window length is odd and at least 5
    window_length = max(5, window_length)
    if window_length % 2 == 0:
        window_length += 1
    
    # Save original data
    T_orig = T.copy()
    F_orig = F.copy()
    
    # Check if data is already smooth by calculating its noise level
    raw_diff = np.diff(F)
    raw_noise = np.std(raw_diff)
    
    # Optional: Interpolate data for smoother curves
    # Create a finer temperature grid with 3x more points
    if enable_interpolation and len(T) > 20:  # Only interpolate if enabled and we have enough points
        T_fine = np.linspace(T.min(), T.max(), len(T) * 3)
        # Use cubic interpolation for smoother curves
        F_interp = interp1d(T, F, kind='cubic')
        # Get interpolated fluorescence values
        F_fine = F_interp(T_fine)
        # Use the interpolated data for further processing
        T, F = T_fine, F_fine
    
    # Primary smoothing of F - use lower polyorder for smoother results
    if len(F) >= window_length:
        # Use lower polyorder for initial smoothing to ensure it's actually smooth
        smooth_F = savgol_filter(F, window_length=window_length, polyorder=sg_poly_order)
        
        # Check if our smoothing actually helped
        smooth_diff = np.diff(smooth_F)
        smooth_noise = np.std(smooth_diff)
        
        # If smoothing made things worse, try a larger window or lower polyorder
        if smooth_noise > raw_noise:
            larger_window = min(len(F) - 1, window_length * 2 + 1)
            if larger_window > window_length and larger_window % 2 == 1:
                # Try again with larger window
                smooth_F = savgol_filter(F, window_length=larger_window, polyorder=sg_poly_order)
            else:
                # Try again with lower polyorder (if current is 3, try 2, if 2 try 1)
                fallback_poly_order = max(1, sg_poly_order -1)
                smooth_F = savgol_filter(F, window_length=window_length, polyorder=fallback_poly_order)
    else:
        # For very short arrays, use a simple moving average
        smooth_F = np.convolve(F, np.ones(5)/5, mode='same')
    
    # First derivative of smoothed_F
    raw_derivative = np.gradient(smooth_F, T)
    
    # Apply dampening to reduce edge artifacts
    damped_derivative = apply_edge_dampening(raw_derivative, fraction=0.1)
    
    # Secondary smoothing of the dampened derivative - use larger window for derivative
    deriv_window = min(window_length, len(damped_derivative) - 1)
    if deriv_window % 2 == 0:
        deriv_window -= 1  # Ensure odd window length
    
    if deriv_window >= 5:
        smooth_derivative = savgol_filter(damped_derivative, window_length=deriv_window, polyorder=sg_poly_order)
    else:
        # For very short arrays, minimal smoothing
        smooth_derivative = damped_derivative
    
    # For large window sizes, also calculate a less-smoothed derivative for peak refinement
    if window_length > 30:
        # Calculate a less-smoothed derivative for peak position refinement
        refine_window = min(25, len(damped_derivative) - 1)
        if refine_window % 2 == 0:
            refine_window -= 1
        if refine_window >= 5:
            refine_derivative = savgol_filter(damped_derivative, window_length=refine_window, polyorder=sg_poly_order)
        else:
            refine_derivative = damped_derivative
    else:
        refine_derivative = smooth_derivative
    
    # --- Peak Detection --- #

    # Option 1: Gaussian Deconvolution for peak detection
    if use_deconvolution:
        num_gaussians_to_fit = 2 if return_all_peaks else 1
        
        # Determine valid range (exclude edges)
        edge_buffer_deconv = max(15, window_length) # Consistent with edge_buffer later
        if len(T) <= 2 * edge_buffer_deconv + 10: # Check if T is too short for deconv valid range
            # Fallback for very short arrays if trying deconvolution
            abs_deriv = np.abs(smooth_derivative)
            peak_idx_fallback = np.argmax(abs_deriv)
            tm_value_fallback = T[peak_idx_fallback if peak_idx_fallback < len(T) else 0]
            additional_peaks_list = [] 
            if enable_interpolation:
                return tm_value_fallback, smooth_F, smooth_derivative, peak_idx_fallback, additional_peaks_list, T, T_orig, F_orig
            else:
                return tm_value_fallback, smooth_F, smooth_derivative, peak_idx_fallback, additional_peaks_list

        valid_T_deconv = T[edge_buffer_deconv:-edge_buffer_deconv]
        valid_deriv_deconv = smooth_derivative[edge_buffer_deconv:-edge_buffer_deconv]
        
        # Focus on the protein melting range (typically 40-90°C), can be adjusted
        deconv_temp_range = (40, 90) 
        
        # Call deconvolute_peaks and get all fitted parameters (Gaussians + baseline)
        # and the data for individual Gaussian components
        fitted_model_params, deconv_peaks_data = deconvolute_peaks(
            valid_T_deconv, valid_deriv_deconv, 
            num_peaks=num_gaussians_to_fit, 
            temp_range=deconv_temp_range
        )
        
        tm_value_deconv = np.nan
        peak_idx_global_deconv = np.nan
        all_potential_peaks_deconv = [] # This will be the list for the 5th return value

        if deconv_peaks_data:
            processed_peaks = []
            for peak_params in deconv_peaks_data:
                # Map temperature back to the full T array to get a global index
                peak_temp = peak_params['temp']
                # Ensure the temperature is within the original T range if interpolated
                current_T_array_for_idx = T # This is T_fine if interpolated, else original T
                global_idx = np.argmin(np.abs(current_T_array_for_idx - peak_temp))

                # Construct a peak dictionary similar to find_peaks path
                # SNR from deconvolution is often calculated differently, ensure consistency or note it.
                # For now, use the SNR from deconv_peaks_data directly.
                peak_info = {
                    'type': 'peak', # Deconvolution usually aims for peaks representing transitions
                    'temp': peak_temp,
                    'idx_global': global_idx,
                    'snr': peak_params.get('snr', 5.0), # Use provided SNR or a default
                    'height': peak_params.get('height', np.abs(peak_params.get('amplitude', 0))),
                    'width': peak_params.get('width', 1.0),
                    'amplitude': peak_params.get('amplitude'),
                    'deconvolved': True
                }
                if enable_interpolation:
                    peak_info['orig_idx'] = np.argmin(np.abs(T_orig - peak_temp))
                processed_peaks.append(peak_info)
            
            processed_peaks.sort(key=lambda p: p['temp']) # Sort by temperature

            # Generate and attach the fitted Gaussian curve(s) for plotting
            # The fitted_model_params contains all parameters for Gaussians + baseline
            if processed_peaks and fitted_model_params is not None and len(fitted_model_params) > 0:
                # T here is the temperature array used for deconvolution (T_fine if interpolated, or original T)
                # multi_gaussian will use all parameters in fitted_model_params to create the composite curve
                fitted_curve_plot_data = multi_gaussian(T, *fitted_model_params)
                for p_info in processed_peaks: # Attach the composite curve to all processed deconvolved peaks
                    p_info['fitted_curve'] = fitted_curve_plot_data
            
            # Determine primary Tm and the list of peaks to return based on mode
            if return_all_peaks: # Multi-peak mode
                all_potential_peaks_deconv = processed_peaks # Return all deconvolved peaks
                if all_potential_peaks_deconv: 
                    # Select primary Tm: prioritize by largest absolute amplitude for deconv peaks
                    sorted_by_abs_amp = sorted(all_potential_peaks_deconv, key=lambda p: np.abs(p.get('amplitude', 0)), reverse=True)
                    if sorted_by_abs_amp:
                        best_peak = sorted_by_abs_amp[0]
                        tm_value_deconv = best_peak['temp']
                        peak_idx_global_deconv = best_peak['idx_global']
                    else: # Should not happen if all_potential_peaks_deconv has items
                         tm_value_deconv, peak_idx_global_deconv = (np.nan, np.nan)
                else: # No peaks from deconvolution
                    tm_value_deconv, peak_idx_global_deconv = (np.nan, np.nan)
            else: # Single-peak mode (num_gaussians_to_fit was 1)
                if processed_peaks: # Should be one peak if deconvolution was successful for num_peaks=1
                    best_peak = processed_peaks[0] 
                    tm_value_deconv = best_peak['temp']
                    peak_idx_global_deconv = best_peak['idx_global']
                    # Ensure the single deconvolved peak with its fitted_curve is returned
                    all_potential_peaks_deconv = processed_peaks 
                # If processed_peaks is empty, tm_value_deconv remains NaN, handled by fallback below
        
        # Fallback if deconvolution provided no usable peaks (or tm_value_deconv is still NaN)
        if np.isnan(tm_value_deconv):
            abs_deriv = np.abs(smooth_derivative)
            peak_idx_global_deconv = np.argmax(abs_deriv)
            if peak_idx_global_deconv < len(T):
                 tm_value_deconv = T[peak_idx_global_deconv]
            else: # Should not happen if T is not empty
                 tm_value_deconv = T[0] if len(T) > 0 else np.nan
            # all_potential_peaks_deconv would be empty here from initialization

        if enable_interpolation:
            return tm_value_deconv, smooth_F, smooth_derivative, peak_idx_global_deconv, all_potential_peaks_deconv, T, T_orig, F_orig
        else:
            return tm_value_deconv, smooth_F, smooth_derivative, peak_idx_global_deconv, all_potential_peaks_deconv
        
    # Option 2: Standard peak detection method (if not using deconvolution)
    # Determine valid search range (exclude beginning and end where artifacts often occur)
    edge_buffer = max(15, window_length)  # Increased buffer size
    
    if len(smooth_derivative) < 2 * edge_buffer + 10:
        # For very short arrays, fall back to simple approach
        abs_deriv = np.abs(smooth_derivative)
        max_abs_idx = np.argmax(abs_deriv)
        peak_idx = max_abs_idx if max_abs_idx < len(T) else len(T) -1 
        peak_idx = max(0, peak_idx) 
        tm_value = T[peak_idx] if peak_idx < len(T) and len(T) > 0 else np.nan
        
        if enable_interpolation:
            # T is T_fine if interpolation happened, T_orig is the original T before interpolation block
            return tm_value, smooth_F, smooth_derivative, peak_idx, [], T, T_orig, F_orig
        else:
            return tm_value, smooth_F, smooth_derivative, peak_idx, []
    
    # Get valid region for analysis
    valid_region = smooth_derivative[edge_buffer:-edge_buffer]
    valid_temps = T[edge_buffer:-edge_buffer]

    # Define refine_peak_position function here, before it's called
    def refine_peak_position(initial_idx, search_radius=10):
        """Refine peak position using less-smoothed derivative"""
        # initial_idx is expected to be local to the start of where refine_derivative was sliced,
        # or local to valid_region (which corresponds to where smooth_derivative was sliced)
        global_idx = initial_idx + edge_buffer  # Convert local peak index from valid_region to global T index
        
        # Define search range on the global T (and refine_derivative) arrays
        start_idx = max(0, global_idx - search_radius)
        end_idx = min(len(refine_derivative), global_idx + search_radius + 1)
        
        segment = refine_derivative[start_idx:end_idx]
        
        if len(segment) == 0:
            return global_idx # Return original global_idx if segment is empty
        
        # Determine if it was a peak or dip based on the more smoothed derivative at the original global_idx
        # Ensure global_idx is within bounds for smooth_derivative
        is_positive_peak = False
        if 0 <= global_idx < len(smooth_derivative):
            if smooth_derivative[global_idx] >= 0:
                is_positive_peak = True
        elif len(segment) > 0 : # Fallback if global_idx is out of bounds for smooth_derivative
             # Guess based on the sign of the segment max/min relative to segment mean or ends
            if segment[np.argmax(np.abs(segment))] > 0: # Simplified check
                 is_positive_peak = True

        if is_positive_peak:
            local_max_idx_in_segment = np.argmax(segment)
        else:
            local_max_idx_in_segment = np.argmin(segment)
        
        refined_global_idx = start_idx + local_max_idx_in_segment
        return refined_global_idx

    # Find all significant features (both peaks and dips)
    # Find positive peaks with more sensitive parameters and lower distance requirement
    pos_peaks, pos_props = find_peaks(valid_region, 
                                     height=0.05*np.max(valid_region),  # Reduced height threshold further (was 0.1)
                                     prominence=0.05*np.max(valid_region),  # Reduced prominence threshold further (was 0.08)
                                     width=1.5,  # Reduced width to catch subtle shoulder peaks (was 2)
                                     distance=3)  # Allow peaks to be even closer (was 5)

    # Find negative peaks (dips) - with stricter parameters to avoid baseline fluctuations
    neg_peaks, neg_props = find_peaks(-valid_region, 
                                     height=0.2*np.max(-valid_region),  # Keep increased height threshold
                                     prominence=0.15*np.max(-valid_region),  # Keep increased prominence threshold
                                     width=3)

    # Combine all detected features
    all_peaks = []
    peak_properties = []

    # Add positive peaks - these are more reliable for protein unfolding
    for i, pk in enumerate(pos_peaks):
        all_peaks.append(pk)
        peak_properties.append({
            'type': 'peak',
            'temp': valid_temps[pk],
            'height': pos_props['peak_heights'][i],
            'prominence': pos_props['prominences'][i],
            'width': pos_props['widths'][i],
            'idx': pk
        })

    # Add negative peaks (dips) with extra validation
    for i, pk in enumerate(neg_peaks):
        # Additional check for dips - they should be well-defined
        if neg_props['prominences'][i] > 0.2 * np.max(neg_props['prominences']) and neg_props['widths'][i] >= 3:
            all_peaks.append(pk)
            peak_properties.append({
                'type': 'dip',
                'temp': valid_temps[pk],
                'height': neg_props['peak_heights'][i],
                'prominence': neg_props['prominences'][i],
                'width': neg_props['widths'][i],
                'idx': pk
            })

    # If no significant features found, fall back to maximum absolute change
    if not all_peaks: # all_peaks here is list of indices from find_peaks
        abs_valid = np.abs(valid_region)
        peak_idx_local = np.argmax(abs_valid) # local index in valid_region
        peak_idx_global = peak_idx_local + edge_buffer
        tm_value = T[peak_idx_global]
        
        if enable_interpolation:
            # T is T_fine if interpolation happened, T_orig is the original T before interpolation block
            return tm_value, smooth_F, smooth_derivative, peak_idx_global, [], T, T_orig, F_orig
        else:
            return tm_value, smooth_F, smooth_derivative, peak_idx_global, []

    # Calculate SNR for each peak/dip
    for i, peak_info in enumerate(peak_properties):
        idx = peak_info['idx']
        
        # Calculate SNR using the calculated function
        snr_value = calculate_snr(valid_region, idx, window_size=max(5, int(peak_info['width'])))
        peak_properties[i]['snr'] = snr_value

    # If we're returning all peaks for user selection, do minimal filtering
    if return_all_peaks:
        # Only filter out obvious noise and peaks outside typical protein range
        all_potential_peaks = []
        for peak in peak_properties:
            temp = peak['temp']
            snr = peak['snr']
            width = peak['width']
            peak_type = peak['type']
            
            # Basic filtering to remove obvious noise - more permissive for shoulder peaks
            in_range = 35 <= temp <= 95  # Wider temperature range
            min_snr = 1.0 if peak_type == 'peak' else 2.0  # Lower SNR requirements for peaks (was 1.5)
            min_width = 1.0 if peak_type == 'peak' else 2.0  # Lower width requirements for peaks (was 1.5)
            
            if in_range and snr >= min_snr and width >= min_width:
                # Add global index
                peak['idx_global'] = peak['idx'] + edge_buffer
                
                # Refine peak position if window size is large
                if window_length > 30:
                    refined_idx = refine_peak_position(peak['idx'], search_radius=10)
                    if 0 <= refined_idx < len(T):
                        peak['idx_global'] = refined_idx
                        peak['temp'] = T[refined_idx]
                
                all_potential_peaks.append(peak)
        
        # Sort by SNR
        all_potential_peaks.sort(key=lambda p: p['snr'], reverse=True)
        
        # Still need to return a primary peak for the main results table
        if all_potential_peaks:
            # Prefer positive peaks over dips for the primary
            pos_peaks = [p for p in all_potential_peaks if p['type'] == 'peak']
            if pos_peaks:
                best_peak = pos_peaks[0]
            else:
                best_peak = all_potential_peaks[0]
                
            peak_idx_global = best_peak['idx_global']
            tm_value = best_peak['temp']
        else:
            # Fallback if no peaks found
            abs_valid = np.abs(valid_region)
            peak_idx = np.argmax(abs_valid)
            peak_idx_global = peak_idx + edge_buffer
            tm_value = T[peak_idx_global]
            
        # If we interpolated, map the results back to original temperature scale for display
        if 'T_orig' in locals():
            # Keep the smooth_derivative on the fine grid for better visualization
            # But map the peak indices to the original temperature array
            for peak in all_potential_peaks:
                # Find the closest temperature in the original array
                peak_temp = peak['temp']
                orig_idx = np.argmin(np.abs(T_orig - peak_temp))
                # Update the global index to match the original array
                peak['orig_idx'] = orig_idx
                
        return tm_value, smooth_F, smooth_derivative, peak_idx_global, all_potential_peaks
    
    # Original filtering logic for standard mode
    # Apply temperature range filtering (typical protein melting range)
    # but allow high SNR features outside this range
    filtered_peaks = []
    for peak in peak_properties:
        temp = peak['temp']
        snr = peak['snr']
        width = peak['width']
        peak_type = peak['type']
        
        # Check if in typical protein melting range
        in_typical_range = 45 <= temp <= 90
        
        # High SNR threshold (consider features with very high SNR even if outside typical range)
        high_snr = snr > 5.0
        
        # Different width requirements based on peak type
        good_width = (width >= 3) if peak_type == 'dip' else (width >= 2)
        
        # Higher SNR requirement for dips since they're often noise
        min_snr = 3.0 if peak_type == 'dip' else 2.0
        
        # Include the peak if it meets criteria based on type
        if (in_typical_range or high_snr) and good_width and snr >= min_snr:
            filtered_peaks.append(peak)
            
    # If all peaks were filtered out, use all peaks
    if not filtered_peaks:
        # Try relaxing criteria for peaks only (more reliable)
        peaks_only = [p for p in peak_properties if p['type'] == 'peak']
        if peaks_only:
            filtered_peaks = sorted(peaks_only, key=lambda p: p['snr'], reverse=True)
        else:
            filtered_peaks = peak_properties

    # Special handling for closely spaced peaks with similar heights
    # Group peaks by proximity
    def group_by_proximity(peaks, temp_threshold=7.0):
        """Group peaks that are close to each other"""
        if not peaks:
            return []
        
        # Sort peaks by temperature
        sorted_peaks = sorted(peaks, key=lambda p: p['temp'])
        
        # Initialize groups
        groups = [[sorted_peaks[0]]]
        
        # Group peaks that are close to each other
        for peak in sorted_peaks[1:]:
            last_group = groups[-1]
            last_peak = last_group[-1]
            
            # If this peak is close to the last one, add it to the same group
            if abs(peak['temp'] - last_peak['temp']) <= temp_threshold:
                last_group.append(peak)
            else:
                # Start a new group
                groups.append([peak])
        
        return groups

    # Group peaks by proximity
    peak_groups = group_by_proximity([p for p in filtered_peaks if p['type'] == 'peak'], temp_threshold=7.0)

    # For each group, ensure we keep multiple peaks if they have similar prominence
    enhanced_peaks = []
    for group in peak_groups:
        if len(group) <= 1:
            # Single peak, just add it
            enhanced_peaks.extend(group)
            continue
        
        # Sort group by SNR
        sorted_group = sorted(group, key=lambda p: p['snr'], reverse=True)
        best_peak = sorted_group[0]
        best_snr = best_peak['snr']
        
        # Always keep the best peak
        enhanced_peaks.append(best_peak)
        
        # Add additional peaks if they're at least 70% as prominent as the best one
        for peak in sorted_group[1:]:
            if peak['snr'] >= 0.7 * best_snr:
                enhanced_peaks.append(peak)
            
    # Add back any dips we had
    dips = [p for p in filtered_peaks if p['type'] == 'dip']
    enhanced_peaks.extend(dips)

    # Replace filtered_peaks with our enhanced selection
    filtered_peaks = enhanced_peaks

    # Sort by SNR
    filtered_peaks.sort(key=lambda p: p['snr'], reverse=True)

    # Look for shoulder peaks explicitly - peaks that are close in proximity to higher peaks
    # and may have been filtered out
    shoulder_candidates = []
    for peak in peak_properties:
        if peak in filtered_peaks:
            continue  # Skip peaks we've already selected
        
        # Only consider peaks (not dips) for shoulders since they're more reliable
        if peak['type'] != 'peak':
            continue
        
        temp = peak['temp']
        snr = peak['snr']
        width = peak['width']
        
        # Shoulder peaks should be close to a main peak but not too close
        has_nearby_peak = False
        for main_peak in filtered_peaks:
            temp_diff = abs(temp - main_peak['temp'])
            if 3.0 <= temp_diff <= 15.0:  # Within reasonable shoulder distance
                has_nearby_peak = True
                break
            
        # Shoulders should still have reasonable SNR and width
        if has_nearby_peak and snr >= 1.5 and width >= 2:
            shoulder_candidates.append(peak)
        
    # Add top shoulder candidates to filtered_peaks
    if shoulder_candidates:
        # Sort by SNR
        shoulder_candidates.sort(key=lambda p: p['snr'], reverse=True)
        # Add up to 2 best shoulder peaks
        for candidate in shoulder_candidates[:2]:
            if candidate not in filtered_peaks:
                filtered_peaks.append(candidate)
        
        # Sort all peaks by SNR again
        filtered_peaks.sort(key=lambda p: p['snr'], reverse=True)

    # Check if we have multiple significant peaks
    # We'll define significant as having SNR > 25% of the highest peak's SNR
    additional_peaks = []

    if len(filtered_peaks) > 1:
        top_snr = filtered_peaks[0]['snr']
        # Use a lower threshold for secondary peak detection to catch more potential transitions
        min_snr_threshold = 0.25 * top_snr  # 25% of top SNR
        min_temp_separation = 2.0  # Reduced from 2.5 to 2.0 to better detect close transitions
        
        # Find additional significant peaks
        for i, peak in enumerate(filtered_peaks[1:], 1):  # Skip the highest peak which is our primary Tm
            # Check if this peak is significant
            if peak['snr'] > min_snr_threshold:
                # Check if it's not too close to a higher-SNR peak
                is_distinct = True
                for j, higher_peak in enumerate(filtered_peaks[:i]):
                    if abs(peak['temp'] - higher_peak['temp']) < min_temp_separation:
                        is_distinct = False
                        break
                
                if is_distinct:
                    additional_peaks.append({
                        'temp': peak['temp'],
                        'idx': peak['idx'] + edge_buffer,  # Global index
                        'snr': peak['snr'],
                        'type': peak['type']
                    })
                    
                    # Only need to keep track of the top additional peak for most applications
                    # (but we'll allow up to 3 for complex unfolding)
                    if len(additional_peaks) >= 3:
                        # Sort by SNR and keep the highest SNR peaks
                        additional_peaks.sort(key=lambda p: p['snr'], reverse=True)
                        if len(additional_peaks) > 3:
                            additional_peaks = additional_peaks[:3]  # Keep only the top 3

    # Ensure we're reporting the primary Tm correctly
    # For protein unfolding, positive peaks (actual unfolding) should be prioritized over dips
    best_peak = filtered_peaks[0]
    primary_peak_type = best_peak['type']

    # If our top peak is a dip, check if we have a high-SNR positive peak to use instead
    if primary_peak_type == 'dip':
        positive_peaks = [p for p in filtered_peaks if p['type'] == 'peak']
        if positive_peaks and positive_peaks[0]['snr'] > 0.7 * best_peak['snr']:
            best_peak = positive_peaks[0]  # Use the best positive peak instead

    peak_idx_global = best_peak['idx'] + edge_buffer
    tm_value = T[peak_idx_global]
    
    # AFTER we've identified peaks, refine their positions using the less-smoothed derivative
    # This function will be called for each peak we want to refine
    # def refine_peak_position(initial_idx, search_radius=10): # MOVED EARLIER
    # ... (rest of the function definition was here)
    
    # After we've identified all peaks, apply the refinement
    # This happens just before returning the results
    
    # Refine the primary peak position
    if not np.isnan(peak_idx_global) and peak_idx_global < len(T):
        refined_idx = refine_peak_position(peak_idx_global - edge_buffer)
        if 0 <= refined_idx < len(T):
            peak_idx_global = refined_idx
            tm_value = T[peak_idx_global]
    
    # Refine additional peak positions
    refined_additional_peaks = []
    for peak in additional_peaks:
        if 'idx' in peak and peak['idx'] is not None:
            original_idx = peak['idx']
            refined_idx = refine_peak_position(original_idx - edge_buffer)
            
            # Create a copy of the peak with refined position
            refined_peak = peak.copy()
            refined_peak['idx'] = refined_idx
            refined_peak['temp'] = T[refined_idx] if 0 <= refined_idx < len(T) else peak['temp']
            refined_additional_peaks.append(refined_peak)
        else:
            refined_additional_peaks.append(peak)
    
    # Consolidate the list of peaks to be returned into `all_potential_peaks` variable,
    # as this is what the final return statements use.
    if not return_all_peaks:
        # If `return_all_peaks` is False, the standard filtering logic (lines 601-834) was used.
        # The results are in `refined_additional_peaks` or `additional_peaks`.
        if 'refined_additional_peaks' in locals() and refined_additional_peaks is not None:
            all_potential_peaks = refined_additional_peaks
        elif 'additional_peaks' in locals() and additional_peaks is not None: # `additional_peaks` is from line 730
            all_potential_peaks = additional_peaks
        else:
            all_potential_peaks = [] # No peaks found by standard filtering
    elif 'all_potential_peaks' not in locals():
         # This case implies return_all_peaks was True, but all_potential_peaks didn't get set
         # (e.g. if the non-deconv, return_all_peaks=True path failed to set it and didn't return early).
         # This is a safeguard.
         all_potential_peaks = []

    # At the end of the function, return interpolation information if needed
    if enable_interpolation:
        current_T = T # This T is T_fine if interpolation happened, else original T
        return tm_value, smooth_F, smooth_derivative, peak_idx_global, all_potential_peaks, current_T, T_orig, F_orig
    else:
        return tm_value, smooth_F, smooth_derivative, peak_idx_global, all_potential_peaks 

def calc_tm_polynomial_fit(T, deriv_curve, peak_indices, window_half_width_points=5):
    """
    Calculates Tm by fitting a 2nd order polynomial to the region around a peak
    in the derivative curve.

    Args:
        T (np.ndarray): Temperature array.
        deriv_curve (np.ndarray): Derivative curve (dF/dT).
        peak_indices (list or np.ndarray): Indices of peaks found by find_peaks.
        window_half_width_points (int): Number of points to include on each side of the peak
                                        for polynomial fitting.

    Returns:
        list: A list of dictionaries, where each dictionary contains:
              'Tm_poly': The Tm determined by the polynomial fit.
              'peak_index': The original index of the peak.
              'coeffs': The polynomial coefficients [a, b, c] for ax^2 + bx + c.
              'r_squared': R-squared value of the fit.
              'area_poly': The area under the polynomial fit within the window.
    """
    tms_poly = []
    if len(T) == 0 or len(deriv_curve) == 0 or len(peak_indices) == 0:
        return tms_poly

    for pk_idx in peak_indices:
        start_idx = max(0, pk_idx - window_half_width_points)
        end_idx = min(len(T) - 1, pk_idx + window_half_width_points)

        # Ensure we have enough points for a quadratic fit (at least 3)
        # and that the window actually contains points
        if end_idx - start_idx + 1 < 3 :
            continue

        T_window = T[start_idx : end_idx + 1]
        deriv_window = deriv_curve[start_idx : end_idx + 1]

        if len(T_window) < 3: # Double check after slicing
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

            tms_poly.append({
                'Tm_poly': tm_val,
                'peak_index': pk_idx,
                'coeffs': coeffs.tolist(),
                'r_squared': r_squared,
                'area_poly': area_poly, # Added polynomial area
                'T_window_used': T_window.tolist(), # For debugging or visualization
                'deriv_window_used': deriv_window.tolist() # For debugging or visualization
            })
        except (np.linalg.LinAlgError, ValueError) as e:
            # print(f"Polynomial fit failed for peak at index {pk_idx}: {e}")
            # Optionally, could append a result indicating failure or use find_peaks Tm
            tms_poly.append({
                'Tm_poly': T[pk_idx], # Fallback
                'peak_index': pk_idx,
                'coeffs': None,
                'r_squared': 0.0,
                'area_poly': np.nan, # Area is undefined if fit failed
                'error': str(e)
            })
            
    return tms_poly 