#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plot functions for nanoDSF data visualization
"""
import numpy as np
import matplotlib.pyplot as plt
from analysis import boltzmann_exp, hill4


def plot_tm_curve(T_raw, F_raw, T_processed=None, popt=None, tm_idx=None, smooth=None, deriv=None, method="boltzmann",
               figsize=(8, 4), additional_peaks=None, polynomial_fit_details=None):
    """
    Plot TM curve with optional fit and derivative
    
    Parameters:
        T_raw (np.ndarray): Temperature array for raw data
        F_raw (np.ndarray): Fluorescence array for raw data
        T_processed (np.ndarray, optional): Temperature array for processed data (smooth, deriv). 
                                         If None, T_raw is used.
        popt (np.ndarray, optional): Optimized parameters for Boltzmann fit
        tm_idx (int, optional): TM peak index for derivative method (relative to T_processed or T_raw)
        smooth (np.ndarray, optional): Smoothed fluorescence data (should correspond to T_processed or T_raw)
        deriv (np.ndarray, optional): Derivative data (should correspond to T_processed or T_raw)
        method (str): Analysis method ('boltzmann' or 'derivative' or 'auc')
        figsize (tuple): Figure size
        additional_peaks (list, optional): List of additional peaks to mark on the derivative plot.
                                         Indices should be relative to T_processed or T_raw.
        polynomial_fit_details (dict, optional): Details for polynomial fit
        
    Returns:
        list: List of created figures
    """
    figures = []
    
    # Determine the T-axis for processed data (smooth, deriv, and peak indices)
    T_for_processing = T_processed if T_processed is not None else T_raw
    
    if method == "boltzmann":
        # Boltzmann fit is typically on raw data
        fig1, ax1 = plt.subplots(figsize=figsize)
        ax1.plot(T_raw, F_raw, '.', label='Raw data')
        
        if popt is not None:
            # Generate fit curve on T_raw
            ax1.plot(T_raw, boltzmann_exp(T_raw, *popt), '-', label='Boltzmann fit')
            # Mark TM point
            tm_value = popt[6]  # Tm is the 7th parameter
            ax1.axvline(tm_value, color='red', linestyle='--', label=f'TM = {tm_value:.2f}°C')
        
        ax1.set_xlabel('Temperature (°C)')
        ax1.set_ylabel('Fluorescence')
        ax1.legend()
        figures.append(fig1)
        
    elif method == "derivative":
        # Plot raw data
        fig1, ax1 = plt.subplots(figsize=figsize)
        ax1.plot(T_raw, F_raw, '.', markersize=2, alpha=0.7, label='Raw data')
        
        if smooth is not None:
            if len(T_for_processing) == len(smooth):
                ax1.plot(T_for_processing, smooth, '-', linewidth=2, label='Smoothed data')
            else:
                # This indicates a mismatch that should ideally be resolved upstream
                # For now, attempt to plot with a warning if lengths differ
                print(f"Warning: Mismatch in lengths for smoothed data plotting. T: {len(T_for_processing)}, Smooth: {len(smooth)}")
                min_len = min(len(T_for_processing), len(smooth))
                ax1.plot(T_for_processing[:min_len], smooth[:min_len], '-', linewidth=2, label='Smoothed data (trimmed)')
        
        ax1.set_xlabel('Temperature (°C)')
        ax1.set_ylabel('Fluorescence')
        ax1.legend()
        figures.append(fig1)
        
        # Plot derivative
        if deriv is not None:
            fig2, ax2 = plt.subplots(figsize=figsize)
            
            # Ensure T_for_processing has enough points for edge_trim
            if len(T_for_processing) > 20 : # Arbitrary threshold to allow trimming
                edge_trim = min(10, len(T_for_processing) // 20)
            else:
                edge_trim = 0


            if len(T_for_processing) == len(deriv):
                if edge_trim == 0 or (len(T_for_processing) - 2 * edge_trim > 0) :
                     ax2.plot(T_for_processing[edge_trim:-edge_trim], deriv[edge_trim:-edge_trim], '-', linewidth=2, label='dF/dT')
                else: # Not enough points to trim
                     ax2.plot(T_for_processing, deriv, '-', linewidth=2, label='dF/dT (no trim)')
            else:
                print(f"Warning: Mismatch in lengths for derivative data plotting. T: {len(T_for_processing)}, Deriv: {len(deriv)}")
                min_len = min(len(T_for_processing), len(deriv))
                # Recalculate safe_edge_trim based on min_len
                safe_edge_trim = 0
                if min_len > 20:
                    safe_edge_trim = min(10, min_len // 20)
                
                if safe_edge_trim == 0 or (min_len - 2 * safe_edge_trim > 0):
                    ax2.plot(T_for_processing[:min_len][safe_edge_trim:-safe_edge_trim if safe_edge_trim > 0 else min_len], 
                             deriv[:min_len][safe_edge_trim:-safe_edge_trim if safe_edge_trim > 0 else min_len], 
                             '-', linewidth=2, label='dF/dT (trimmed)')
                else:
                     ax2.plot(T_for_processing[:min_len], deriv[:min_len], '-', linewidth=2, label='dF/dT (no trim)')

            # Check if we have deconvolved peaks with fitted curves
            has_deconvolved_peaks = False
            composite_fit_plotted = False # Initialize flag
            if additional_peaks:
                for peak in additional_peaks:
                    if isinstance(peak, dict) and peak.get('deconvolved', False) and 'fitted_curve' in peak:
                        has_deconvolved_peaks = True
                        # The 'fitted_curve' is on the T_for_processing axis
                        break
            
            # Check if we have polynomial fitted peaks
            has_polynomial_fitted_peaks = False
            if additional_peaks:
                for peak in additional_peaks:
                    if isinstance(peak, dict) and peak.get('polynomial_fitted', False) and 'fitted_curve' in peak:
                        has_polynomial_fitted_peaks = True
                        break
            
            if has_deconvolved_peaks:
                for peak in additional_peaks: # This loop is to find the first available 'fitted_curve'
                    if 'fitted_curve' in peak and peak.get('deconvolved', False): # Ensure it's from deconvolution
                        fitted_curve = peak['fitted_curve']
                        # Ensure fitted_curve corresponds to T_for_processing
                        if len(T_for_processing) == len(fitted_curve):
                             ax2.plot(T_for_processing, fitted_curve, '--', color='purple', linewidth=1.5, label='Gaussian fit')
                             composite_fit_plotted = True # Set flag as composite fit is plotted
                        else:
                            print(f"Warning: Mismatch in lengths for Gaussian fit plotting. T: {len(T_for_processing)}, Fit: {len(fitted_curve)}")
                        break # Plot only one composite fitted_curve
                
                # Only plot individual Gaussian components if the composite fit was NOT plotted
                if not composite_fit_plotted:
                    colors = ['red', 'green', 'blue', 'orange', 'cyan']
                    for i, peak in enumerate(additional_peaks):
                        if peak.get('deconvolved', False): # Check if it's a deconvolved peak
                            amp = peak.get('amplitude', 0)
                            cen = peak.get('temp', 0) # temp is absolute
                            wid = peak.get('width', 1)
                            
                            # Individual Gaussian curves should be generated on a fine version of T_for_processing or its range
                            gaussian_x = np.linspace(T_for_processing.min(), T_for_processing.max(), 200)
                            gaussian_y = amp * np.exp(-(gaussian_x - cen)**2 / (2 * wid**2))
                            color = colors[i % len(colors)]
                            
                            label = f'Peak {i+1} (Tm={cen:.2f}°C)'
                            if len(additional_peaks) == 1: # Or if only one deconvolved peak is present
                                num_deconv_peaks = sum(1 for p in additional_peaks if p.get('deconvolved', False))
                                if num_deconv_peaks == 1:
                                    label = f'Gaussian fit (Tm={cen:.2f}°C)' # This was causing the red line
                            
                            ax2.plot(gaussian_x, gaussian_y, '-', color=color, linewidth=1, alpha=0.7, label=label)
            
            # Plot polynomial fitted curves
            elif has_polynomial_fitted_peaks:
                for peak in additional_peaks:
                    if peak.get('polynomial_fitted', False) and 'fitted_curve' in peak and 'T_fit_curve' in peak:
                        T_fit_curve = peak['T_fit_curve']
                        fitted_curve = peak['fitted_curve']
                        
                        if len(T_fit_curve) == len(fitted_curve) and len(T_fit_curve) > 0:
                            ax2.plot(T_fit_curve, fitted_curve, '--', color='red', linewidth=2, alpha=0.8, 
                                   label=f'Polynomial fit (±3°C)')
                            break  # Only plot one polynomial curve to avoid clutter
            
            marked_temps = set()
            all_transitions_display = [] # Renamed to avoid conflict
            
            # Primary transition - use polynomial Tm if available
            primary_tm_value = None
            primary_tm_source = "find_peaks"
            
            # Check if polynomial fit was used and has results
            if polynomial_fit_details:
                # Try different possible locations for polynomial Tm
                poly_tm = None
                
                # First try direct access
                poly_tm = polynomial_fit_details.get('Tm_poly')
                
                # If not found, try polynomial_info nested structure
                if poly_tm is None:
                    poly_info = polynomial_fit_details.get('polynomial_info', {})
                    poly_tm = poly_info.get('Tm_poly')
                
                # If still not found, try polynomial_coeffs approach 
                if poly_tm is None and polynomial_fit_details.get('polynomial_coeffs'):
                    # Calculate Tm from polynomial coefficients if available
                    coeffs = polynomial_fit_details.get('polynomial_coeffs')
                    if coeffs and len(coeffs) >= 3 and coeffs[0] != 0:  # ax² + bx + c, a ≠ 0
                        a, b = coeffs[0], coeffs[1]
                        poly_tm = -b / (2 * a)  # Vertex of parabola
                
                # Last resort: extract from T_window_used if available
                if poly_tm is None:
                    T_window = polynomial_fit_details.get('T_window_used')
                    deriv_window = polynomial_fit_details.get('deriv_window_used')
                    if T_window and deriv_window and len(T_window) == len(deriv_window):
                        # Find the temperature corresponding to max derivative in the window
                        max_idx = np.argmax(deriv_window)
                        poly_tm = T_window[max_idx]
                
                if poly_tm is not None and not np.isnan(poly_tm):
                    primary_tm_value = poly_tm
                    primary_tm_source = "polynomial"
            
            # Fallback to tm_idx if no polynomial result
            if primary_tm_value is None and tm_idx is not None and not np.isnan(tm_idx):
                tm_idx = int(tm_idx)
                if 0 <= tm_idx < len(T_for_processing):
                    primary_tm_value = T_for_processing[tm_idx]
                    primary_tm_source = "tm_idx"
            
            # Add primary transition to display list
            if primary_tm_value is not None:
                all_transitions_display.append({
                    'temp': primary_tm_value, 
                    'label': 'Low Tm', 
                    'color': 'red', 
                    'priority': 1,
                    'source': primary_tm_source
                })
                marked_temps.add(round(primary_tm_value, 2))
            
            # Additional transitions from additional_peaks (indices relative to T_for_processing)
            # Skip additional peaks if polynomial fitting is used (to avoid showing find_peaks results)
            if additional_peaks and not polynomial_fit_details:
                for i, peak in enumerate(additional_peaks):
                    if isinstance(peak, dict):
                        peak_temp_val = peak.get('temp') # Absolute temperature
                        peak_idx_val = peak.get('idx')   # Index on T_for_processing

                        current_peak_temp = np.nan
                        if peak_idx_val is not None and 0 <= peak_idx_val < len(T_for_processing):
                            current_peak_temp = T_for_processing[peak_idx_val]
                        elif peak_temp_val is not None: # Fallback to temp if idx is invalid/missing
                            current_peak_temp = peak_temp_val
                            if peak_idx_val is None: # If idx was missing, try to find it
                                peak_idx_val = np.argmin(np.abs(T_for_processing - current_peak_temp))

                        if np.isnan(current_peak_temp): continue

                        rounded_temp = round(current_peak_temp, 2)
                        if rounded_temp in marked_temps: continue
                            
                        # Fix redundant labeling: check if label already contains temperature
                        raw_label = peak.get('label', f'Transition {i+1}')
                        if '=' in raw_label and '°C' in raw_label:
                            # Label already contains temperature (e.g., "Tm 1 = 65.52°C")
                            label = raw_label
                        else:
                            # Label doesn't contain temperature, add it
                            label = f"{raw_label} = {current_peak_temp:.2f}°C"
                        
                        color = peak.get('color', 'purple')
                        
                        # Adjust label/color for deconvolved peaks if not explicitly set
                        if peak.get('deconvolved', False) and ('label' not in peak or 'color' not in peak):
                            is_primary_deconv = not any(t['deconvolved'] for t in all_transitions_display if t['temp'] < current_peak_temp)
                            label = f"{'Low Tm' if is_primary_deconv else 'High Tm'} = {current_peak_temp:.2f}°C"
                            color = 'red' if is_primary_deconv else 'green'
                                
                        all_transitions_display.append({
                            'temp': current_peak_temp, 'label': label, 'color': color, 
                            'idx': peak_idx_val, 'priority': 2, 
                            'deconvolved': peak.get('deconvolved', False)
                        })
                        marked_temps.add(rounded_temp)
            
            # Sort transitions by temperature for consistent ordering
            all_transitions_display.sort(key=lambda x: x['temp'])
            
            # Plot the transition markers
            for transition in all_transitions_display:
                # Check if the label already contains the temperature to avoid redundancy
                label = transition['label']
                if '=' in label and '°C' in label:
                    # Label already formatted with temperature
                    final_label = label
                else:
                    # Add temperature to label
                    final_label = f"{label} = {transition['temp']:.2f}°C"
                
                ax2.axvline(transition['temp'], color=transition['color'], linestyle='--', 
                           label=final_label)
            
            ax2.set_xlabel('Temperature (°C)')
            ax2.set_ylabel('dF/dT')
            ax2.legend()
            figures.append(fig2)
    
    elif method == "auc":
        # Plot raw data and processed data for AUC method
        fig1, ax1 = plt.subplots(figsize=figsize)
        ax1.plot(T_raw, F_raw, '.', markersize=2, alpha=0.7, label='Raw data')
        
        # If we have auc_result data, plot additional information
        auc_data = additional_peaks  # For AUC method, additional_peaks contains auc result data
        if auc_data and isinstance(auc_data, dict):
            method_used = auc_data.get('method', 'unknown')
            
            # Mark Tm point
            tm_auc = auc_data.get('Tm_AUC')
            if tm_auc is not None and not np.isnan(tm_auc):
                ax1.axvline(tm_auc, color='red', linestyle='--', linewidth=2, 
                           label=f'Tm (AUC) = {tm_auc:.2f}°C')
        
        ax1.set_xlabel('Temperature (°C)')
        ax1.set_ylabel('Fluorescence')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        figures.append(fig1)
        
        # Plot cumulative area for derivative method
        if auc_data and isinstance(auc_data, dict) and 'cumulative_area' in auc_data:
            cumulative_area = auc_data['cumulative_area']
            if len(cumulative_area) > 0:
                fig2, ax2 = plt.subplots(figsize=figsize)
                
                temp_range = auc_data.get('temperature_range', T_raw)
                
                if len(temp_range) == len(cumulative_area):
                    ax2.plot(temp_range, cumulative_area, '-', linewidth=2, 
                            label='Cumulative Area (Derivative)', color='blue')
                    
                    # Mark 50% point
                    total_area = auc_data.get('total_area', cumulative_area[-1] if len(cumulative_area) > 0 else 0)
                    if total_area > 0:
                        area_50_percent = total_area * 0.5
                        ax2.axhline(area_50_percent, color='red', linestyle='--', alpha=0.7, label='50% Area')
                        
                        # Mark Tm point
                        tm_auc = auc_data.get('Tm_AUC')
                        if tm_auc is not None and not np.isnan(tm_auc):
                            ax2.axvline(tm_auc, color='red', linestyle='--', 
                                       label=f'Tm (AUC) = {tm_auc:.2f}°C')
                
                ax2.set_xlabel('Temperature (°C)')
                ax2.set_ylabel('Cumulative Area')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
                figures.append(fig2)
    
    return figures


def plot_ec50_curve(conc, tm_values, errors=None, popt=None, figsize=(8, 6)):
    """
    Plot EC50 dose-response curve
    
    Parameters:
        conc (np.ndarray): Concentration array
        tm_values (np.ndarray): TM values array
        errors (np.ndarray, optional): Standard errors for TM values
        popt (np.ndarray, optional): Optimized parameters for Hill equation
        figsize (tuple): Figure size
        
    Returns:
        matplotlib.figure.Figure: Created figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot experimental data with error bars
    if errors is not None:
        ax.errorbar(conc, tm_values, yerr=errors, fmt='o', label='Data ± SE')
    else:
        ax.scatter(conc, tm_values, label='Data')
    
    # Plot fit curve if parameters are provided
    if popt is not None:
        # Generate smooth curve for plotting
        x_smooth = np.logspace(np.log10(conc.min()/2), np.log10(conc.max()*2), 200)
        y_smooth = hill4(x_smooth, *popt)
        ec50 = popt[2]  # EC50 is the 3rd parameter
        ax.semilogx(x_smooth, y_smooth, '-', label=f'Fit EC₅₀={ec50:.2e} M')
    
    ax.set_xlabel('Concentration (M)')
    ax.set_ylabel('TM (°C)')
    ax.legend()
    
    return fig


def plot_delta_tm(sample_names, delta_tm_values, errors=None, figsize=(10, 6)):
    """
    Plot delta TM bar chart for screening
    
    Parameters:
        sample_names (list): List of sample names
        delta_tm_values (np.ndarray): Delta TM values array
        errors (np.ndarray, optional): Standard errors for delta TM values
        figsize (tuple): Figure size
        
    Returns:
        matplotlib.figure.Figure: Created figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create bar chart
    if errors is not None:
        ax.bar(sample_names, delta_tm_values, yerr=errors)
    else:
        ax.bar(sample_names, delta_tm_values)
    
    # Rotate x labels for better readability
    ax.set_xticklabels(sample_names, rotation=45, ha='right')
    ax.set_ylabel('ΔTM (°C)')
    
    # Add zero line
    ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    
    return fig 