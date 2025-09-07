#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
I/O utility functions for nanoDSF data
"""
import os
import zipfile
import io
import pandas as pd
import numpy as np
from .parser import parse_concentration
import re

# Set up debug mode for this function
global enable_debug_mode
enable_debug_mode = False

def read_zip_data(file_obj, channel, method, window_length=21, progress_callback=None, enable_multi_peak=False, enable_interpolation=False, derivative_peak_method='find_peaks', sg_poly_order=2, auc_method='derivative', auc_baseline_correction=True, auc_smoothing_window=11, auc_interpolation_factor=3, debug_mode=False):
    """
    Process nanoDSF data from a ZIP archive
    
    Parameters:
        file_obj: File-like object containing the ZIP archive
        channel (str): Data channel to use ('350/330 nm ratio', '350 nm', '330 nm')
        method (str): Analysis method ('Two-state Boltzmann', 'First derivative')
        window_length (int): Window length for Savitzky-Golay filtering
        progress_callback (callable): Optional callback function to report progress
        enable_multi_peak (bool): Whether to detect and report multiple transitions
        enable_interpolation (bool): Whether to use interpolation for smoother curves
        derivative_peak_method (str): Method for derivative peak finding ('find_peaks', 'gaussian_deconvolution', 'polynomial_fit')
        sg_poly_order (int): Polynomial order for Savitzky-Golay filter (default 2)
        auc_method (str): Method for AUC analysis ('derivative', 'cumulative')
        auc_baseline_correction (bool): Whether to apply baseline correction for AUC analysis
        auc_smoothing_window (int): Window length for smoothing in AUC analysis
        auc_interpolation_factor (int): Interpolation factor for AUC analysis
        debug_mode (bool): Whether to enable debug mode
        
    Returns:
        tuple: (DataFrame with results, dictionary with capillary data, list of csv file names used)
    """
    from analysis import analyze_tm_derivative, analyze_tm_boltzmann
    from analysis.calc import calc_tm_auc
    
    results = []
    cap_data = {}
    csv_files_processed = [] # To store names of CSVs actually processed
    
    # Set up debug mode for this function
    global enable_debug_mode
    enable_debug_mode = debug_mode
    
    # Define debug logging function
    def log_debug(message):
        if debug_mode:
            print(f"[DEBUG] {message}")
            # Also add to Streamlit session state for UI display
            try:
                import streamlit as st
                if hasattr(st, 'session_state') and hasattr(st.session_state, 'global_debug_log'):
                    st.session_state.global_debug_log.append(f"[AUC] {message}")
            except:
                pass  # Ignore if streamlit not available or session_state not set
    
    log_debug(f"=== read_zip_data called with debug_mode={debug_mode}, method='{method}' ===")
    
    with zipfile.ZipFile(file_obj, "r") as z:
        all_files_in_zip = z.namelist()
        # Filter for raw.csv files initially - this list is used for detection later
        relevant_csv_names_for_detection = sorted([f for f in all_files_in_zip if f.lower().endswith("raw.csv")])
        
        if not relevant_csv_names_for_detection:
            # If no raw.csv files at all, return empty results and the empty list of names
            return pd.DataFrame(), {}, [] 
        
        total_files_to_process = 0 # Will count files that match channel criteria
        files_matching_channel = []

        for csv_path in relevant_csv_names_for_detection:
            # Pre-filter by channel to count total_files_to_process accurately
            original_csv_path = csv_path # Keep original name for parsing conc, etc.
            # Ensure csv_path for channel matching is just the filename if it includes full path from zip
            csv_filename_for_channel_match = os.path.basename(csv_path).lower()

            passes_channel_filter = False
            if channel.startswith("350/330") and 'ratio' in csv_filename_for_channel_match:
                passes_channel_filter = True
            elif channel == '350 nm' and '350nm' in csv_filename_for_channel_match.replace(" ", "") and 'ratio' not in csv_filename_for_channel_match:
                passes_channel_filter = True
            elif channel == '330 nm' and '330nm' in csv_filename_for_channel_match.replace(" ", "") and 'ratio' not in csv_filename_for_channel_match:
                passes_channel_filter = True
            
            if passes_channel_filter:
                files_matching_channel.append(original_csv_path)
        
        total_files_to_process = len(files_matching_channel)
        if total_files_to_process == 0:
            # No files matched the selected channel criteria
            return pd.DataFrame(), {}, relevant_csv_names_for_detection # Return all raw.csv names for detection

        log_debug(f"Starting to process {total_files_to_process} files matching channel '{channel}'")

        for i, csv_path in enumerate(files_matching_channel):
            csv_files_processed.append(csv_path) # Add to list of processed files
            rep = os.path.splitext(os.path.basename(csv_path))[0]
            conc = parse_concentration(csv_path) # Use original path for concentration parsing
            
            if progress_callback:
                progress_callback(i+1, total_files_to_process, rep)
            
            # Read CSV data (already filtered by channel and raw.csv extension)
            raw = z.read(csv_path)
            df = pd.read_csv(io.BytesIO(raw), sep='\t')
            df.columns = [c.strip() for c in df.columns]
            
            T = df['T[°C]'].values
            F = df[df.columns[1]].values
            
            if len(T) != len(F) or len(T) < 10:
                continue
            
            log_debug(f"Processing capillary {rep} with method '{method}' (type: {type(method)})")
            
            if method.startswith("First derivative"):
                log_debug(f"Processing capillary {rep} with First derivative method")
                # Call analyze_tm_derivative with the new tm_method parameter
                analysis_args = {
                    'T': T, 'F': F, 
                    'window_length': window_length, 
                    'return_all_peaks': enable_multi_peak,
                    'enable_interpolation': enable_interpolation, 
                    'sg_poly_order': sg_poly_order,
                    'tm_method': derivative_peak_method # Pass the new method parameter
                }
                
                tm_results_dict = analyze_tm_derivative(**analysis_args)

                # Unpack from the dictionary returned by analyze_tm_derivative
                Tm = tm_results_dict.get('tm_value', np.nan)
                smooth = tm_results_dict.get('smooth_F')
                deriv = tm_results_dict.get('smooth_derivative')
                tm_idx = tm_results_dict.get('peak_index_global', np.nan)
                additional_peaks = tm_results_dict.get('all_potential_peaks', [])
                
                cap_data_rep = {
                    'T': tm_results_dict.get('T_original') if enable_interpolation else T,
                    'F': tm_results_dict.get('F_original') if enable_interpolation else F,
                    'smooth': smooth,
                    'deriv': deriv,
                    'is_interpolated': enable_interpolation,
                    'tm_idx': tm_idx,
                    'additional_peaks': additional_peaks,
                    'details': tm_results_dict.get('details', {})
                }
                if enable_interpolation:
                    cap_data_rep['T_interp'] = tm_results_dict.get('T_processed')
                
                cap_data[rep] = cap_data_rep
                
                snr = np.nan # Placeholder, actual SNR calc follows
                if not np.isnan(tm_idx) and deriv is not None and len(deriv) > 0:
                    idx_for_snr = int(tm_idx)
                    len_deriv = len(deriv)
                    if 0 <= idx_for_snr < len_deriv: # Ensure index is valid
                        base_values = []
                        if len_deriv > 60:
                            if idx_for_snr > 35: base_values.extend(deriv[10:30])
                            if idx_for_snr < len_deriv - 35: base_values.extend(deriv[len_deriv-30:len_deriv-10])
                        if not base_values and len_deriv > 20:
                            segment_len = max(5, len_deriv // 4)
                            if idx_for_snr > segment_len + 2: base_values.extend(deriv[:segment_len])
                            if idx_for_snr < len_deriv - (segment_len + 2): base_values.extend(deriv[-segment_len:])
                        base_array = np.array(base_values)
                        if base_array.size > 1 and base_array.std() != 0:
                            snr = (deriv[idx_for_snr] - base_array.mean()) / base_array.std()
                
                ci_low = ci_high = se = r2 = log_dAIC = np.nan
                if enable_multi_peak and additional_peaks:
                    cap_data[rep]['additional_peaks'] = additional_peaks

                # Store deconvolution/polynomial fit specific information if available
                if derivative_peak_method == 'gaussian_deconvolution':
                    cap_data[rep]['deconvolved'] = True # Mark that deconvolution was attempted/used
                    # Details from Gaussian fit (like individual peak parameters) are in tm_results_dict['all_potential_peaks']
                    # and potentially tm_results_dict['details']
                elif derivative_peak_method == 'polynomial_fit':
                    cap_data[rep]['polynomial_fit_details'] = tm_results_dict.get('details', {})
            elif method == "Two-state Boltzmann": # Boltzmann
                log_debug(f"Processing capillary {rep} with Two-state Boltzmann method")
                Tm, (ci_low, ci_high), se, snr, r2, log_dAIC, popt, pcov = analyze_tm_boltzmann(T, F)
                cap_data[rep] = {'T': T, 'F': F, 'popt': popt}
            elif method == "AUC": # AUC method
                log_debug(f"Processing capillary {rep} with AUC method")
                # Call AUC analysis with the provided parameters
                auc_result = calc_tm_auc(T, F, method=auc_method, baseline_correction=auc_baseline_correction, 
                                       smoothing_window=auc_smoothing_window, interpolation_factor=auc_interpolation_factor)
                
                # Debug: Log AUC result details
                log_debug(f"AUC analysis for capillary {rep}: success={auc_result.get('success', False)}")
                if not auc_result.get('success', False):
                    log_debug(f"AUC failure details: {auc_result}")
                else:
                    log_debug(f"AUC Tm: {auc_result.get('Tm_AUC', 'N/A')}, Quality: {auc_result.get('quality_score', 'N/A')}")
                
                if auc_result.get('success', False):
                    Tm = auc_result['Tm_AUC']
                    # For AUC, we use quality score as a substitute for SNR
                    snr = auc_result.get('quality_score', 0.0) * 10  # Scale to SNR-like range
                    r2 = auc_result.get('quality_score', 0.0)  # Quality score as R² substitute
                    
                    cap_data[rep] = {
                        'T': T, 
                        'F': F, 
                        'auc_result': auc_result,
                        'total_area': auc_result.get('total_area', np.nan),
                        'cumulative_area': auc_result.get('cumulative_area', []),
                        'temperature_range': auc_result.get('temperature_range', T)
                    }
                else:
                    Tm = np.nan
                    snr = 0.0
                    r2 = 0.0
                    cap_data[rep] = {'T': T, 'F': F, 'auc_result': auc_result}
                
                # AUC doesn't provide confidence intervals, standard error, or AIC
                ci_low = ci_high = se = log_dAIC = np.nan
            else:
                # Fallback for unknown methods
                log_debug(f"Unknown method '{method}' - using fallback")
                Tm = np.nan
                ci_low = ci_high = se = snr = r2 = log_dAIC = np.nan
                cap_data[rep] = {'T': T, 'F': F}
            
            flag = "" # Initialize flag as empty
            if method.startswith("First derivative"):
                # For First Derivative
                if not np.isnan(snr) and snr < 2.5:
                    flag = "⚠️"
            elif method == "Two-state Boltzmann":
                # For Two-State Boltzmann
                conditions_tsb = [
                    (not np.isnan(se) and se > 1),
                    (not np.isnan(snr) and snr < 5),
                    (not np.isnan(log_dAIC) and log_dAIC < 1)
                ]
                if any(conditions_tsb):
                    flag = "⚠️"
            elif method == "AUC":
                # For AUC method
                if not np.isnan(snr) and snr < 5.0:  # Quality score * 10 < 5.0 means quality < 0.5
                    flag = "⚠️"
            
            results.append({
                'Capillary': rep, 'TM (°C)': Tm, 'CI Lower': ci_low, 'CI Upper': ci_high,
                'SE (°C)': se, 'State SNR': snr, 'R²': r2, 'log ΔAIC': log_dAIC,
                'Flag': flag, 'Sample Info': '', 'Concentration': conc
            })
    
    # Return all raw.csv names found in the zip for experiment type detection,
    # regardless of channel filtering for actual processing.
    return pd.DataFrame(results), cap_data, relevant_csv_names_for_detection


def detect_experiment_type(csv_names, concentration_threshold=3):
    """
    Detects the experiment type based on concentration diversity in filenames.

    Parameters:
        csv_names (list): List of CSV file names (e.g., from zip archive).
        concentration_threshold (int): Minimum number of unique concentrations 
                                     to classify as 'dose-response'.

    Returns:
        str: 'dose-response' or 'screening'.
    """
    from .parser import parse_concentration # Ensure parse_concentration is available

    if not csv_names:
        return 'screening' # Default if no files

    concentrations = set()
    has_dose_folder = False
    has_sp_folder = False

    for name in csv_names:
        # Check for common folder structures as a hint
        # Use uppercase for case-insensitive comparison and check both path separators
        name_upper = name.upper()
        if 'DOSE/' in name_upper or 'DOSE\\' in name_upper: # Double backslash for literal
            has_dose_folder = True
        if 'SP/' in name_upper or 'SP\\' in name_upper: # Double backslash for literal
            has_sp_folder = True
        
        conc = parse_concentration(name)
        if conc is not None and not np.isnan(conc):
            concentrations.add(float(conc))
    
    # Strong indicator from folder structure
    if has_dose_folder and not has_sp_folder:
        return 'dose-response'
    if has_sp_folder and not has_dose_folder:
        return 'screening'
    
    # Fallback to concentration diversity
    if len(concentrations) > concentration_threshold:
        return 'dose-response'
    else:
        return 'screening'


def get_snr_for_channels(file_obj, analysis_method_name, sg_window_length, debug_log_list=None):
    """
    Analyzes a representative capillary from a ZIP archive across different channels 
    to determine Signal-to-Noise Ratios (SNRs) for each.
    Appends detailed debug information to the provided debug_log_list.
    Returns a tuple: (snrs_dict, representative_cap_name_str)
    """
    from analysis import analyze_tm_derivative, analyze_tm_boltzmann
    from analysis.calc import calc_tm_auc
    import zipfile, io, pandas as pd, numpy as np, os, re

    # Helper to append to log if list is provided
    def log_debug(message):
        if debug_log_list is not None:
            debug_log_list.append(message)

    snrs = {'ratio': np.nan, '350nm': np.nan, '330nm': np.nan}
    representative_cap_name = "N/A (No suitable files found)"
    
    log_debug("--- Starting get_snr_for_channels (v3 prefix logic) ---")
    try:
        with zipfile.ZipFile(file_obj, "r") as z:
            all_raw_csvs = sorted([f for f in z.namelist() if f.lower().endswith("raw.csv")])
            log_debug(f"Found {len(all_raw_csvs)} raw CSVs. First 5: {all_raw_csvs[:5]}...")
            if not all_raw_csvs:
                return snrs, representative_cap_name

            capillary_files = {} 
            # Regex to extract the common prefix AND the channel indicator
            # Group 1: Prefix (e.g., "BCL2+ABT263_1000 - 1")
            # Group 2: Channel indicator (e.g., "_350 nm", "_Ratio")
            # Group 3: Rest of the filename (e.g., "_unfolding_raw")
            prefix_and_channel_pattern = re.compile(r"^(.*?)(_350 nm|_330 nm|_Ratio|_ratio|_350nm|_330nm)(.*)?$", re.IGNORECASE)

            for f_path in all_raw_csvs:
                basename = os.path.splitext(os.path.basename(f_path))[0]
                match = prefix_and_channel_pattern.match(basename)
                
                cap_prefix = None
                channel_indicator_from_regex = None

                if match:
                    cap_prefix = match.group(1).strip() # The part before the channel indicator
                    channel_indicator_from_regex = match.group(2).lower() # The channel indicator itself
                else:
                    # Fallback for files that don't match the detailed pattern (e.g., simple A1.csv)
                    well_id_match = re.match(r"^([A-P][0-9]{1,2})", basename, re.IGNORECASE)
                    if well_id_match:
                        cap_prefix = well_id_match.group(1).upper()
                    else: 
                        cap_prefix = basename # Last resort, might not group well
                
                if not cap_prefix: # Should not happen if basename is not empty
                    continue

                if cap_prefix not in capillary_files:
                    capillary_files[cap_prefix] = {}

                # Determine channel type based on the regex match or simple string check
                if channel_indicator_from_regex:
                    if "ratio" in channel_indicator_from_regex:
                        capillary_files[cap_prefix]['ratio_path'] = f_path
                    elif "350nm" in channel_indicator_from_regex or "350 nm" in channel_indicator_from_regex:
                        capillary_files[cap_prefix]['350nm_path'] = f_path
                    elif "330nm" in channel_indicator_from_regex or "330 nm" in channel_indicator_from_regex:
                        capillary_files[cap_prefix]['330nm_path'] = f_path
                else:
                    # If regex didn't find a channel indicator, resort to basic check on full basename
                    # This is for filenames that don't fit the prefix_and_channel_pattern, e.g. legacy names
                    basename_lower = basename.lower()
                    if "ratio" in basename_lower:
                        capillary_files[cap_prefix]['ratio_path'] = f_path
                    elif "350nm" in basename_lower and "ratio" not in basename_lower:
                         capillary_files[cap_prefix]['350nm_path'] = f_path
                    elif "330nm" in basename_lower and "ratio" not in basename_lower:
                         capillary_files[cap_prefix]['330nm_path'] = f_path
            
            log_debug(f"Built capillary_files map for {len(capillary_files)} unique prefixes. Example: {dict(list(capillary_files.items())[:1]) if capillary_files else 'None'}")
            if capillary_files:
                 example_prefix_to_log = list(capillary_files.keys())[0]
                 log_debug(f"  Example content for prefix '{example_prefix_to_log}': {capillary_files[example_prefix_to_log]}")
            
            target_cap_paths_dict = None
            sorted_cap_prefixes = sorted(capillary_files.keys(), key=lambda k: (len(k), k)) 
            
            for cap_prefix_iter in sorted_cap_prefixes:
                files_dict_iter = capillary_files[cap_prefix_iter]
                if 'ratio_path' in files_dict_iter and \
                   '350nm_path' in files_dict_iter and \
                   '330nm_path' in files_dict_iter:
                    target_cap_paths_dict = files_dict_iter
                    representative_cap_name = cap_prefix_iter
                    log_debug(f"Found ideal cap group '{representative_cap_name}' with all 3 channel files: {target_cap_paths_dict}")
                    break
            
            if not target_cap_paths_dict:
                log_debug("No single prefix group has all three files. Switching to Fallback (Mixed mode)...")
                representative_cap_name = "Mixed (first available of each type)"
                target_cap_paths_dict = {
                    'ratio_path': next((f for f in all_raw_csvs if "ratio" in os.path.splitext(os.path.basename(f))[0].lower()), None),
                    '350nm_path': next((f for f in all_raw_csvs if "350nm" in os.path.splitext(os.path.basename(f))[0].lower() and "ratio" not in os.path.splitext(os.path.basename(f))[0].lower()), None),
                    '330nm_path': next((f for f in all_raw_csvs if "330nm" in os.path.splitext(os.path.basename(f))[0].lower() and "ratio" not in os.path.splitext(os.path.basename(f))[0].lower()), None)
                }
                if not any(target_cap_paths_dict.values()):
                    log_debug("Fallback (Mixed) also found no suitable files for any channel type.")
                    return snrs, representative_cap_name
                log_debug(f"Fallback (Mixed) mode paths: {target_cap_paths_dict}")

            channel_file_map = {
                'ratio': target_cap_paths_dict.get('ratio_path'),
                '350nm': target_cap_paths_dict.get('350nm_path'),
                '330nm': target_cap_paths_dict.get('330nm_path')
            }
            log_debug(f"Final channel_file_map: {channel_file_map}")

            for channel_key, csv_path_to_process in channel_file_map.items():
                log_debug(f"Processing channel: {channel_key}, File: {csv_path_to_process}")
                if not csv_path_to_process:
                    log_debug(f"  -> No file found for {channel_key}")
                    continue
                
                try:
                    raw_data = z.read(csv_path_to_process)
                    df_snr_check = pd.read_csv(io.BytesIO(raw_data), sep='\t')
                    df_snr_check.columns = [c.strip() for c in df_snr_check.columns]
                    T_snr = df_snr_check['T[°C]'].values
                    F_snr = df_snr_check[df_snr_check.columns[1]].values
                    log_debug(f"  -> Read data for {channel_key}: T shape {T_snr.shape}, F shape {F_snr.shape}")

                    if len(T_snr) != len(F_snr) or len(T_snr) < 10:
                        log_debug(f"  -> Short or mismatched data for {channel_key}. Skipping.")
                        continue

                    current_snr_val = np.nan
                    if analysis_method_name.startswith("First derivative"):
                        tm_val, _, deriv_vals, tm_idx_val, _ = analyze_tm_derivative(
                            T_snr, F_snr, sg_window_length, 
                            return_all_peaks=False, enable_interpolation=False, use_deconvolution=False,
                            sg_poly_order=2 # For SNR pre-check, always use polyorder 2 for consistency
                        )
                        log_debug(f"  -> For {channel_key}, Derivative analysis: Tm={tm_val}, tm_idx={tm_idx_val}")
                        if not np.isnan(tm_idx_val) and deriv_vals is not None and len(deriv_vals) > 0:
                            idx_for_snr_calc = int(tm_idx_val)
                            if idx_for_snr_calc >= len(deriv_vals): idx_for_snr_calc = len(deriv_vals) -1
                            if idx_for_snr_calc < 0: idx_for_snr_calc = 0
                            
                            len_deriv_calc = len(deriv_vals)
                            base_values_calc = []
                            if len_deriv_calc > 60:
                                if idx_for_snr_calc > 35 and (idx_for_snr_calc - 10) > 30 : base_values_calc.extend(deriv_vals[10:30])
                                if idx_for_snr_calc < len_deriv_calc - 35 and (len_deriv_calc - 30) < (len_deriv_calc -10) : base_values_calc.extend(deriv_vals[len_deriv_calc-30:len_deriv_calc-10])
                            elif len_deriv_calc > 20:
                                segment_len = max(5, len_deriv_calc // 4)
                                if idx_for_snr_calc > segment_len + 2 and segment_len > 0: base_values_calc.extend(deriv_vals[:segment_len])
                                if idx_for_snr_calc < len_deriv_calc - (segment_len + 2) and (len_deriv_calc - segment_len) < len_deriv_calc : base_values_calc.extend(deriv_vals[-segment_len:])
                            log_debug(f"  -> For {channel_key}, Baseline points count: {len(base_values_calc)}")
                            base_array_calc = np.array(base_values_calc)
                            if base_array_calc.size > 1 and base_array_calc.std() != 0:
                                current_snr_val = (deriv_vals[idx_for_snr_calc] - base_array_calc.mean()) / base_array_calc.std()
                                log_debug(f"  -> For {channel_key}, Calculated Deriv SNR: {current_snr_val}")
                            else:
                                log_debug(f"  -> For {channel_key}, Deriv SNR not calculated (baseline std={base_array_calc.std() if base_array_calc.size > 1 else 'N/A'} or size <=1)")
                        else:
                             log_debug(f"  -> For {channel_key}, Deriv SNR not calculated (tm_idx_val is NaN or no deriv_vals)")
                    elif analysis_method_name == "AUC":
                        # For AUC method, skip detailed SNR calculation and use a reasonable default
                        current_snr_val = 5.0  # Reasonable default for AUC
                        log_debug(f"  -> For {channel_key}, Using default AUC SNR: {current_snr_val}")
                    else: # Boltzmann
                        _, _, _, snr_boltz_calc, _, _, _, _ = analyze_tm_boltzmann(T_snr, F_snr)
                        current_snr_val = snr_boltz_calc
                        log_debug(f"  -> For {channel_key}, Calculated Boltzmann SNR: {current_snr_val}")
                    snrs[channel_key] = current_snr_val
                except Exception as e:
                    snrs[channel_key] = np.nan 
                    log_debug(f"  -> ERROR processing {channel_key} ({csv_path_to_process}): {type(e).__name__} - {str(e)}")

            if all(pd.isna(s) for s in snrs.values()):
                 representative_cap_name += " (All SNRs NaN)"
            elif pd.isna(snrs['350nm']) and pd.isna(snrs['330nm']):
                representative_cap_name += " (350/330nm SNRs NaN)"
            
            log_debug(f"--- Finished get_snr_for_channels. Returning SNRs: {snrs} ---")
            return snrs, representative_cap_name

    except Exception as e:
        log_debug(f"Overall ERROR in get_snr_for_channels: {type(e).__name__} - {str(e)}")
        return snrs, representative_cap_name # Still return SNRs, even if all NaN 