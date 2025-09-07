#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TM analysis module
"""
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t
from .calc import boltzmann_exp, calc_tm_derivative, calc_tm_polynomial_fit


def analyze_tm_derivative(T, F, window_length=21, return_all_peaks=False, enable_interpolation=False, sg_poly_order=2, tm_method='find_peaks'):
    """
    Analyze TM using first derivative method, with selectable core algorithm.
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        window_length (int): Savitzky-Golay filter window length
        return_all_peaks (bool): Whether to return all potential peaks (for multi-peak detection modes like find_peaks or deconvolution)
        enable_interpolation (bool): Whether to use interpolation for smoother curves
        sg_poly_order (int): Polynomial order for Savitzky-Golay filter (default 2)
        tm_method (str): Method to determine Tm. Options: 'find_peaks', 'gaussian_deconvolution', 'polynomial_fit'.
        
    Returns:
        dict: A dictionary containing TM results and processed data. Keys include:
              'tm_value': The primary melting temperature.
              'peak_area': Area of the primary peak (if calculable by the method).
              'tm_method_used': The method used for Tm determination.
              'smooth_F': Smoothed fluorescence curve.
              'smooth_derivative': Smoothed derivative curve.
              'peak_index_global': Index of the primary peak in the (potentially interpolated) T array.
              'all_potential_peaks': List of other detected peaks/features.
              'T_processed': Temperature array corresponding to smooth_F and smooth_derivative.
              'T_original': Original temperature array (if interpolation was used).
              'F_original': Original fluorescence array (if interpolation was used).
              'details': Method-specific details (e.g., R-squared for polynomial fit).
    """
    
    results_dict = {
        'tm_value': np.nan,
        'peak_area': np.nan,
        'tm_method_used': tm_method,
        'smooth_F': None,
        'smooth_derivative': None,
        'peak_index_global': np.nan,
        'all_potential_peaks': [],
        'T_processed': T, # Will be updated if interpolation happens
        'T_original': None,
        'F_original': None,
        'details': {}
    }

    # Common data preparation: Call calc_tm_derivative to get smoothed curves and initial peak info.
    # For polynomial fit, we use find_peaks results from calc_tm_derivative as input.
    # For gaussian_deconvolution, calc_tm_derivative handles it internally.
    # For find_peaks, calc_tm_derivative with use_deconvolution=False gives the desired result.

    use_deconvolution_for_calc = (tm_method == 'gaussian_deconvolution')
    
    # Call the core calculation function from the .calc submodule
    # This function returns (tm_value, smooth_F, smooth_derivative, peak_idx_global, all_potential_peaks)
    # or an extended tuple if enable_interpolation is True.
    calc_results = calc_tm_derivative(
        T, F, 
        window_length=window_length, 
        return_all_peaks=return_all_peaks, # Pass this through
        enable_interpolation=enable_interpolation, 
        use_deconvolution=use_deconvolution_for_calc, 
        sg_poly_order=sg_poly_order
    )

    # Unpack results from calc_tm_derivative
    if enable_interpolation:
        # tm_val_from_calc, sm_F, sm_deriv, pk_idx_calc, pot_peaks_calc, T_interp, T_orig, F_orig = calc_results
        # Assign to results_dict early for clarity
        results_dict['smooth_F'] = calc_results[1]
        results_dict['smooth_derivative'] = calc_results[2]
        results_dict['T_processed'] = calc_results[5] # T_interp
        results_dict['T_original'] = calc_results[6] # T_orig
        results_dict['F_original'] = calc_results[7] # F_orig
        
        # These are specific to find_peaks or gaussian_deconvolution method output from calc_tm_derivative
        tm_val_from_calc = calc_results[0]
        peak_idx_calc = calc_results[3]
        potential_peaks_from_calc = calc_results[4]
    else:
        # tm_val_from_calc, sm_F, sm_deriv, pk_idx_calc, pot_peaks_calc = calc_results
        results_dict['smooth_F'] = calc_results[1]
        results_dict['smooth_derivative'] = calc_results[2]
        results_dict['T_processed'] = T # Original T if no interpolation
        
        tm_val_from_calc = calc_results[0]
        peak_idx_calc = calc_results[3]
        potential_peaks_from_calc = calc_results[4]

    results_dict['peak_index_global'] = peak_idx_calc
    results_dict['all_potential_peaks'] = potential_peaks_from_calc


    if tm_method == 'find_peaks':
        results_dict['tm_value'] = tm_val_from_calc
        # Area is not directly calculated by find_peaks method in calc_tm_derivative
        results_dict['peak_area'] = np.nan 
        # all_potential_peaks is already set from calc_results
        
    elif tm_method == 'gaussian_deconvolution':
        results_dict['tm_value'] = tm_val_from_calc
        # calc_tm_derivative when use_deconvolution=True populates all_potential_peaks
        # with deconvolved peak info, including area.
        # We need to find the primary peak in all_potential_peaks and get its area.
        if results_dict['all_potential_peaks'] and isinstance(results_dict['all_potential_peaks'], list):
            primary_gauss_peak = None
            if not np.isnan(peak_idx_calc):
                # Find the peak corresponding to peak_idx_calc (closest temp)
                # Note: 'idx_global' in deconv peaks list is on the T_processed scale.
                 min_dist = float('inf')
                 for p in results_dict['all_potential_peaks']:
                     if 'idx_global' in p and not np.isnan(p['idx_global']):
                         dist = abs(p['idx_global'] - peak_idx_calc)
                         if dist < min_dist:
                             min_dist = dist
                             primary_gauss_peak = p
                     elif 'temp' in p and not np.isnan(results_dict['tm_value']): # Fallback by temp if idx_global is missing
                        dist_temp = abs(p['temp'] - results_dict['tm_value'])
                        if dist_temp < min_dist :
                            min_dist = dist_temp
                            primary_gauss_peak = p


            if primary_gauss_peak and 'area' in primary_gauss_peak:
                results_dict['peak_area'] = primary_gauss_peak['area']
            elif results_dict['all_potential_peaks']: # Fallback: if primary not clearly ID'd, use first peak's area if available
                if 'area' in results_dict['all_potential_peaks'][0]:
                     results_dict['peak_area'] = results_dict['all_potential_peaks'][0]['area']

    elif tm_method == 'polynomial_fit':
        # We need peak indices from a 'find_peaks' run.
        # The initial call to calc_tm_derivative (with use_deconvolution_for_calc=False if polynomial)
        # should provide these if tm_method was NOT gaussian.
        # If the initial call WAS Gaussian, we need a separate find_peaks run or use its main peak.
        
        # To ensure polynomial fit always has find_peaks indices:
        # Re-run calc_tm_derivative with use_deconvolution=False if the first call was for Gaussian.
        # Or, more simply, ensure the FIRST call to calc_tm_derivative (done above)
        # was effectively a find_peaks call if tm_method is 'polynomial_fit'.
        # This is what `use_deconvolution_for_calc = (tm_method == 'gaussian_deconvolution')` achieves.
        # So, potential_peaks_from_calc should contain find_peaks type data.

        target_peak_indices_for_poly = []
        if not np.isnan(peak_idx_calc): # Use the primary peak from find_peaks
            target_peak_indices_for_poly.append(int(peak_idx_calc))
        
        # Optionally, fit polynomial to all peaks found by find_peaks if return_all_peaks is True
        # For now, just fit to the primary peak identified by the initial find_peaks scan.
        # If `return_all_peaks` is true, `potential_peaks_from_calc` holds them. We could iterate.
        # Let's stick to the primary peak for now for Tm_poly.

        if target_peak_indices_for_poly:
            poly_fit_results = calc_tm_polynomial_fit(
                results_dict['T_processed'], # Use the (potentially interpolated) T array
                results_dict['smooth_derivative'],
                target_peak_indices_for_poly, # Pass as a list
                polynomial_window=3.0 # Use temperature-based window (±3°C)
            )
            if poly_fit_results:
                primary_poly_fit = poly_fit_results[0] # Assuming we fit one peak
                results_dict['tm_value'] = primary_poly_fit.get('Tm_poly', np.nan)
                results_dict['peak_area'] = primary_poly_fit.get('area_poly', np.nan)
                results_dict['details']['polynomial_coeffs'] = primary_poly_fit.get('coeffs')
                results_dict['details']['polynomial_r_squared'] = primary_poly_fit.get('r_squared')
                
                # CRITICAL FIX: Attach polynomial fitted curve data to peak entries for plotting
                # Find the corresponding peak in all_potential_peaks and add the fitted curve data
                primary_peak_idx = target_peak_indices_for_poly[0]
                
                # Add polynomial fitted curve data to the primary peak for visualization
                primary_peak_temp = results_dict['T_processed'][primary_peak_idx] if primary_peak_idx < len(results_dict['T_processed']) else results_dict['tm_value']
                
                # Create a peak entry with polynomial fitted curve data if it doesn't exist or update existing
                polynomial_peak_found = False
                for peak in results_dict['all_potential_peaks']:
                    # Check if this peak corresponds to our polynomial fit target
                    if (isinstance(peak, dict) and 
                        'idx' in peak and peak['idx'] == primary_peak_idx) or \
                       (isinstance(peak, dict) and 
                        'temp' in peak and abs(peak['temp'] - primary_peak_temp) < 2.0):
                        
                        # Add polynomial fitted curve data to this peak
                        peak['polynomial_fitted'] = True
                        peak['Tm_poly'] = primary_poly_fit.get('Tm_poly', peak.get('temp', np.nan))
                        peak['poly_coeffs'] = primary_poly_fit.get('coeffs', None)
                        peak['poly_r_squared'] = primary_poly_fit.get('r_squared', np.nan)
                        peak['poly_area'] = primary_poly_fit.get('area_poly', np.nan)
                        
                        # Add the fitted curve data for plotting
                        peak['T_fit_curve'] = primary_poly_fit.get('T_fit_curve', [])
                        peak['fitted_curve'] = primary_poly_fit.get('fitted_curve', [])
                        
                        polynomial_peak_found = True
                        break
                
                # If no matching peak was found, create a new peak entry
                if not polynomial_peak_found:
                    polynomial_peak = {
                        'temp': primary_peak_temp,
                        'idx': primary_peak_idx,
                        'polynomial_fitted': True,
                        'Tm_poly': primary_poly_fit.get('Tm_poly', results_dict['tm_value']),
                        'poly_coeffs': primary_poly_fit.get('coeffs', None),
                        'poly_r_squared': primary_poly_fit.get('r_squared', np.nan),
                        'poly_area': primary_poly_fit.get('area_poly', np.nan),
                        'T_fit_curve': primary_poly_fit.get('T_fit_curve', []),
                        'fitted_curve': primary_poly_fit.get('fitted_curve', []),
                        'type': 'polynomial'
                    }
                    results_dict['all_potential_peaks'].append(polynomial_peak)
                
                # If we fit multiple, we'd need to decide which one is the primary Tm
            else: # Polynomial fit failed or no peaks to fit
                results_dict['tm_value'] = np.nan # Explicitly set to nan
                results_dict['peak_area'] = np.nan
        else: # No peak_idx_calc to run polynomial fit on
            results_dict['tm_value'] = np.nan
            results_dict['peak_area'] = np.nan
            
    return results_dict


def analyze_tm_boltzmann(T, F):
    """
    Analyze TM using Boltzmann equation
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        
    Returns:
        tuple: (TM value, confidence interval, standard error, state SNR, R², log ΔAIC, optimized parameters, covariance matrix)
    """
    def one_state(T, A, alpha, D):
        return A * np.exp(-alpha * T) + D
    
    # Calculate data characteristics
    F_range = F.max() - F.min()
    F_center = (F.max() + F.min()) / 2
    T_range = T.max() - T.min()
    T_center = (T.max() + T.min()) / 2
    
    # Initial parameters
    p0 = [
        F.max(),     # A_N
        0.005,       # alpha
        F.min(),     # D_N
        F.max()*0.8, # A_D
        0.005,       # beta
        F.min()*1.2, # D_D
        T_center,    # Tm
        0.3          # k
    ]
    
    # Fit single-state model
    try:
        popt1, pcov1 = curve_fit(one_state, T, F, p0=[F.max(), 0.005, F.min()], maxfev=200000)
        y1 = one_state(T, *popt1)
        rss1 = np.sum((F - y1)**2)
    except:
        rss1 = np.sum((F - F.mean())**2)
    
    # Multiple initial parameters fitting
    best_rss = float('inf')
    best_popt = None
    best_pcov = None
    
    initial_params = [
        p0,
        [F.max(), 0.01, F.min(), F.max()*0.9, 0.01, F.min()*1.1, T_center, 0.4],
        [F.max(), 0.003, F.min(), F.max()*0.7, 0.003, F.min()*1.3, T_center, 0.2],
    ]
    
    for p0_try in initial_params:
        try:
            popt2, pcov2 = curve_fit(boltzmann_exp, T, F, p0=p0_try, maxfev=200000)
            y2 = boltzmann_exp(T, *popt2)
            rss2 = np.sum((F - y2)**2)
            
            if rss2 < best_rss:
                best_rss = rss2
                best_popt = popt2
                best_pcov = pcov2
        except:
            continue
    
    if best_popt is None:
        return np.nan, (np.nan, np.nan), np.nan, np.nan, np.nan, np.nan, None, None
    
    # Calculate statistics
    Tm = best_popt[6]
    se = np.sqrt(np.diag(best_pcov))[6]
    dfree = len(T) - len(best_popt)
    tval = t.ppf(0.975, dfree)
    ci = (Tm - tval*se, Tm + tval*se)
    
    # Calculate residuals
    y2 = boltzmann_exp(T, *best_popt)
    resid2 = F - y2
    rss2 = np.sum(resid2**2)
    sigma_resid = np.sqrt(rss2/dfree)
    
    # Calculate state SNR
    A_N, alpha, D_N, A_D, beta, D_D = best_popt[:6]
    FN = A_N*np.exp(alpha*Tm)+D_N
    FD = A_D*np.exp(beta*Tm)+D_D
    deltaF = abs(FD-FN)
    snr_state = deltaF/sigma_resid if sigma_resid else np.nan
    
    # Calculate R²
    ss_tot = np.sum((F-F.mean())**2)
    r2 = 1 - rss2/ss_tot if ss_tot else np.nan
    
    # Calculate AIC
    n = len(T)
    aic1 = n*np.log(rss1/n) + 2*3
    aic2 = n*np.log(rss2/n) + 2*8
    delta_aic = aic1 - aic2
    log_delta_aic = np.log10(delta_aic) if delta_aic > 0 else 0.0
    
    return Tm, ci, se, snr_state, r2, log_delta_aic, best_popt, best_pcov 