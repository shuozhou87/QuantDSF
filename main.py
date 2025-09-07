#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
nanoDSF Tm Calculation & Screening Streamlit App
"""
import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from analysis import (
    boltzmann_exp,
    hill4,
    analyze_ec50,
    analyze_global_fit,
    calculate_delta_tm
)
from utils import read_zip_data, detect_experiment_type, get_snr_for_channels
from visualization import plot_tm_curve, plot_ec50_curve, plot_delta_tm, format_results_table
import zipfile


# Avoid path conflicts if script name matches module
curdir = os.path.dirname(__file__)
if curdir in sys.path:
    sys.path.remove(curdir)
sys.path.insert(0, curdir)


# Page configuration
st.set_page_config(
    page_title="nanoDSF Tm Calculator & Screening",
    layout="wide"
)
st.title("nanoDSF Tm Calculation & Screening App")


# Sidebar settings
st.sidebar.header("Analysis Settings")

# --- Developer Settings (Optional) ---
st.sidebar.markdown("----") # Separator
debug_mode = st.sidebar.checkbox("Enable Debug Mode", value=False, key="debug_mode_checkbox")
st.session_state.debug_mode = debug_mode # Store in session state

# Define channel_options first as it's used by auto-detection logic and selectbox
channel_options = ["350/330 nm ratio", "350 nm", "330 nm"]

# Method selection (needed by auto-channel-check if derivative)
method_options = ["Two-state Boltzmann", "First derivative", "AUC"]
# We need `method` for the SNR check. Define it early, then use it in the check.
# The actual selectbox for method will use this same variable.
# This is a bit of a reordering to make `method` available.
# This is a bit of a reordering to make `method` available.
method_selectbox_value = st.sidebar.selectbox(
    "Select Tm calculation method:",
    method_options,
    key="method_selector_sidebar" # Add a key if not present to ensure state
)
method = method_selectbox_value # Assign to the variable `method` for use

# Initialize session state for derivative_peak_method if it doesn't exist
if 'derivative_peak_method' not in st.session_state:
    st.session_state.derivative_peak_method = 'Find Peaks (Raw Derivative)' # Default value

# Conditional selectbox for derivative peak method
derivative_peak_method_selected = None
if method == "First derivative":
    derivative_method_options = {
        'Find Peaks (Raw Derivative)': 'find_peaks',
        'Gaussian Deconvolution': 'gaussian_deconvolution',
        'Polynomial Fit (Peak Region)': 'polynomial_fit'
    }
    derivative_peak_method_display = st.sidebar.selectbox(
        "Select Derivative Peak Method:",
        options=list(derivative_method_options.keys()),
        key='derivative_peak_method_selector',
        # Use st.session_state to manage the selected index or value if needed for persistence
        # For simplicity, directly use the session state variable for the actual method value later
        index=list(derivative_method_options.keys()).index(st.session_state.derivative_peak_method 
                                                              if st.session_state.derivative_peak_method in derivative_method_options 
                                                              else list(derivative_method_options.keys())[0]) 
    )
    # Update session state with the selected display name for persistence of the selectbox choice
    st.session_state.derivative_peak_method = derivative_peak_method_display
    # Get the corresponding internal method name for analysis function
    derivative_peak_method_selected = derivative_method_options[derivative_peak_method_display]
else:
    # If not First derivative, reset or set a default for derivative_peak_method_selected if necessary
    # or ensure it's not used.
    # st.session_state.derivative_peak_method = list(derivative_method_options.keys())[0] # Reset display state if desired
    derivative_peak_method_selected = 'find_peaks' # Default for non-derivative methods, though it won't be used by analyze_tm_derivative

# Upload data ZIP - This needs to be before the auto-channel check
uploaded_file = st.file_uploader("Upload nanoDSF ZIP archive", type="zip")

# --- Auto-detect best channel on new file upload ---
if "suggested_channel_info" not in st.session_state:
    st.session_state.suggested_channel_info = {"channel": channel_options[0], "message": "", "capillary_checked": "N/A"}
if "last_uploaded_file_for_channel_check" not in st.session_state:
    st.session_state.last_uploaded_file_for_channel_check = None
if "global_debug_log" not in st.session_state: # Ensure global_debug_log is always initialized
    st.session_state.global_debug_log = []

if uploaded_file is not None and uploaded_file.name != st.session_state.get("last_uploaded_file_for_channel_check"):
    st.session_state.last_uploaded_file_for_channel_check = uploaded_file.name
    st.session_state.suggested_channel_info = {"channel": channel_options[0], "message": "", "capillary_checked": "N/A"}
    # Reset/Initialize global_debug_log for the new file check
    st.session_state.global_debug_log = ["New file uploaded. Initializing SNR auto-check..."] 

    window_for_snr_check = 25 
    if method.startswith("First derivative"):
        window_for_snr_check = 25

    uploaded_file.seek(0)
    # Pass the global_debug_log list to get_snr_for_channels
    snrs_from_check, cap_checked = get_snr_for_channels(uploaded_file, method, window_for_snr_check, st.session_state.global_debug_log)
    uploaded_file.seek(0)
    
    snr_ratio = snrs_from_check.get('ratio', np.nan)
    snr_350 = snrs_from_check.get('350nm', np.nan)
    snr_330 = snrs_from_check.get('330nm', np.nan)

    current_best_channel = channel_options[0]
    base_suggestion_text = f"SNRs: Ratio({snr_ratio:.2f}), 350nm({snr_350:.2f}), 330nm({snr_330:.2f}). Cap: {cap_checked}."
    if pd.isna(snr_ratio) and pd.isna(snr_350) and pd.isna(snr_330):
        suggestion_reason = "Could not determine any SNRs for auto-selection. Defaulting to Ratio. " + base_suggestion_text
    else:
        suggestion_reason = "Defaulting to Ratio. " + base_suggestion_text # Default message

    # Logic for suggesting a better channel (remains the same)
    if pd.notna(snr_350) and pd.notna(snr_ratio) and snr_350 > (2 * snr_ratio) and (pd.isna(snr_330) or snr_350 > snr_330):
        current_best_channel = "350 nm"
        suggestion_reason = f"💡 Auto-selected **350nm** (SNR: {snr_350:.2f}) due to significantly better SNR than Ratio (SNR: {snr_ratio:.2f}). Cap: {cap_checked}."
    elif pd.notna(snr_330) and pd.notna(snr_ratio) and snr_330 > (2 * snr_ratio):
        current_best_channel = "330 nm"
        suggestion_reason = f"💡 Auto-selected **330nm** (SNR: {snr_330:.2f}) due to significantly better SNR than Ratio (SNR: {snr_ratio:.2f}). Cap: {cap_checked}."
    elif pd.isna(snr_ratio) and pd.notna(snr_350) and (pd.isna(snr_330) or snr_350 > snr_330):
        current_best_channel = "350 nm"
        suggestion_reason = f"💡 Ratio SNR N/A. Auto-selected **350nm** (SNR: {snr_350:.2f}). Cap: {cap_checked}."
    elif pd.isna(snr_ratio) and pd.isna(snr_350) and pd.notna(snr_330):
        current_best_channel = "330 nm"
        suggestion_reason = f"💡 Ratio & 350nm SNR N/A. Selected **330nm** (SNR: {snr_330:.2f}). Cap: {cap_checked}."
    
    st.session_state.suggested_channel_info = {
        "channel": current_best_channel, 
        "message": suggestion_reason, 
        "capillary_checked": cap_checked
        # No separate "debug_snr_check" needed here anymore, it's in global_debug_log
    }
# --- End of Auto-detect best channel ---

# Stop if no file is uploaded, after the auto-channel check logic that uses uploaded_file
if not uploaded_file:
    st.info("Please upload a ZIP file containing raw CSV files.")
    st.stop()

# Determine initial index for channel selectbox
try:
    # Use .get on session state to handle potential absence of 'channel' key initially
    initial_channel_index = channel_options.index(st.session_state.suggested_channel_info.get("channel", channel_options[0]))
except ValueError:
    initial_channel_index = 0 

# Channel selectbox (method selectbox was moved up)
channel_selectbox_value = st.sidebar.selectbox(
    "Select data channel:",
    channel_options,
    index=initial_channel_index,
    key="channel_selector_sidebar" # Add a key
)
channel = channel_selectbox_value # Assign to variable for use

# Display auto-channel selection message if any
if st.session_state.suggested_channel_info.get("message"):
    st.sidebar.info(st.session_state.suggested_channel_info["message"])
    # The SNR specific debug expander is now removed, global debug area handles it.

# Add multi-peak detection option
enable_multi_peak = st.sidebar.checkbox(
    "Enable multi-peak detection",
    value=False,
    help="Detect multiple transitions in the same sample (for complex unfolding or ligand-induced transitions)"
)

# Add interpolation option
enable_interpolation = st.sidebar.checkbox(
    "Enable curve interpolation",
    value=False,
    help="Use cubic interpolation to create smoother curves (helps detect subtle transitions)"
)

# Display note that multi-peak is most effective with First derivative
if enable_multi_peak and not method.startswith("First derivative"):
    st.sidebar.warning("Note: Multi-peak detection works best with the First derivative method.")

# Display note about interpolation
if enable_interpolation:
    st.sidebar.info("💡 Interpolation creates smoother curves that can help detect subtle shoulder peaks.")

# Initialize AUC parameters with default values (will be overridden if AUC method is selected)
auc_method = 'derivative'
auc_baseline_correction = True
auc_smoothing_window = 11
auc_interpolation_factor = 3

# Initialize window_length with a default value that will be used for all methods
window_length = 25  # Default value for all methods
sg_poly_order = 2  # Default polynomial order

window_help = "Must be odd, higher values give smoother curves but may shift peak positions"

if method.startswith("First derivative"):
    # Calculate a reasonable maximum based on data characteristics and method
    if derivative_peak_method_selected == 'gaussian_deconvolution':
        max_window = 99  # Gaussian deconvolution can handle larger windows better
    else:
        max_window = 99  # Let users choose, but warn them about peak shifting
    
    window_length = st.sidebar.number_input(
        "Savitzky–Golay window length:",
        min_value=5,
        max_value=max_window,
        step=2,
        value=25,  # Use 25 as the default window size for all cases
        help=window_help
    )
    
    # Add polynomial order selection for very noisy data
    sg_poly_order = st.sidebar.selectbox(
        "Polynomial order for smoothing:",
        options=[1, 2, 3],
        index=1,  # Default to 2
        help="Lower order (1) = less smooth but less peak shifting. Higher order (3) = smoother but more shifting risk."
    )
    
    # Enhanced warnings about peak shifting
    if window_length > 25:
        if derivative_peak_method_selected == 'gaussian_deconvolution':
            st.sidebar.info("💡 Gaussian deconvolution compensates for peak shifts from large windows automatically.")
        elif derivative_peak_method_selected == 'polynomial_fit':
            st.sidebar.warning("⚠️ Large windows may shift peaks. Polynomial refinement will correct positions, but verify results.")
        else:
            st.sidebar.warning("⚠️ Large window sizes (>25) can shift peak positions with Find Peaks method. Consider Gaussian Deconvolution for noisy data.")
    
    # Progressive warnings for very large windows
    if window_length > 35:
        st.sidebar.warning("⚠️ Window >35: Risk of significant peak shifting. Compare results with smaller windows.")
    
    if window_length > 51:
        st.sidebar.error("🚨 Window >51: High risk of peak position errors. Use with caution and verify results!")
    
    # Add a note about window size impact when multi-peak detection is enabled
    if enable_multi_peak and derivative_peak_method_selected != 'gaussian_deconvolution':
        st.sidebar.info("💡 Tip: If transitions are missing, try adjusting the window length. Larger values (21-25) usually work well for detecting both main transitions in protein unfolding curves.")

elif method == "AUC":
    st.sidebar.subheader("AUC Analysis Settings")
    
    # Remove the method selection - always use derivative
    auc_method = 'derivative'  # Fixed to derivative only
    
    auc_baseline_correction = st.sidebar.checkbox(
        "Enable baseline correction",
        value=True,
        help="Applies baseline correction to improve transition detection"
    )
    
    auc_smoothing_window = st.sidebar.number_input(
        "Smoothing window size:",
        min_value=5,
        max_value=31,
        step=2,
        value=11,
        help="Window size for signal smoothing (must be odd)"
    )
    
    auc_interpolation_factor = st.sidebar.number_input(
        "Interpolation factor:",
        min_value=1,
        max_value=5,
        value=3,
        help="Factor for data interpolation to increase resolution (1 = no interpolation)"
    )
    
    # For AUC method, use the AUC smoothing window as the main window_length
    window_length = auc_smoothing_window
    
    st.sidebar.info("💡 AUC method uses derivative analysis: calculates area under the absolute derivative curve to find 50% transition point.")

# Table display settings
st.sidebar.header("Table Display Settings")
st.sidebar.caption("Select columns to display in the results table")

# Column display names (more user-friendly names)
column_display_names = {
    "TM (°C)": "Tm (°C)",
    "SE (°C)": "Std Error (°C)",
    "CI Lower": "CI Lower (°C)",
    "CI Upper": "CI Upper (°C)",
    "State SNR": "SNR",
    "R²": "R²",
    "log ΔAIC": "log ΔAIC",
    "Flag": "Quality Flag",
    "Include in EC50": "Include in EC50",
    "Secondary Tm (°C)": "Secondary Tm (°C)",
    "Secondary SNR": "Secondary SNR",
    "Weighted Tm (°C)": "Weighted Tm (°C)"
}

# Default columns to show (essential ones)
default_columns = ["Capillary", "TM (°C)", "State SNR", "Concentration", "Include in EC50"]

# Quick column presets
column_presets = {
    "Minimal": ["Capillary", "TM (°C)", "Concentration", "Include in EC50"],
    "Standard": ["Capillary", "TM (°C)", "State SNR", "SE (°C)", "Flag", "Concentration", "Include in EC50"],
    "Complete": ["Capillary", "TM (°C)", "State SNR", "SE (°C)", "CI Lower", "CI Upper", "R²", "log ΔAIC", "Flag", "Concentration", "Include in EC50"],
}

# If multi-peak detection is enabled, add those columns to the presets
if enable_multi_peak:
    column_presets["Standard"].extend(["Secondary Tm (°C)", "Secondary SNR", "Weighted Tm (°C)"])
    column_presets["Complete"].extend(["Primary Tm (°C)", "Primary SNR", "Secondary Tm (°C)", "Secondary SNR", "Weighted Tm (°C)"])
    # Add a multi-peak specific preset
    column_presets["Multi-peak Focus"] = ["Capillary", "Primary Tm (°C)", "Primary SNR", "Secondary Tm (°C)", "Secondary SNR", "Weighted Tm (°C)", "Concentration", "Include in EC50"]

# Add a preset selector with Standard as default
preset_options = ["Custom"] + list(column_presets.keys())
default_preset_index = preset_options.index("Standard") if "Standard" in preset_options else 0

selected_preset = st.sidebar.selectbox(
    "Column presets:",
    preset_options,
    index=default_preset_index
)

if selected_preset != "Custom":
    selected_columns = column_presets[selected_preset]
    st.sidebar.info(f"Selected preset: {selected_preset}. Customize further below if needed.")
else:
    # Additional columns available for custom selection
    optional_columns = {
        "SE (°C)": True,
        "CI Lower": False,
        "CI Upper": False,
        "R²": False,  # Default to hide R² in custom view
        "Flag": True,
        "log ΔAIC": False,
        "Sample Info": False  # Add Sample Info as an optional column that's hidden by default
    }
    
    # Multi-peak columns (only shown if multi-peak detection is enabled)
    if enable_multi_peak:
        optional_columns.update({
            "Secondary Tm (°C)": True,
            "Secondary SNR": True, 
            "Weighted Tm (°C)": True
        })
    
    # Create checkboxes for optional columns
    selected_columns = default_columns.copy()
    for col, default_state in optional_columns.items():
        display_name = column_display_names.get(col, col)
        if st.sidebar.checkbox(f"Show {display_name}", value=default_state):
            selected_columns.append(col)


# Initialize session state
if "current_dataset" not in st.session_state:
    st.session_state.current_dataset = None
    st.session_state.checkbox_states = {}
    st.session_state.edited_concentrations = {}

# Initialize session state for experiment type
if "experiment_type" not in st.session_state:
    st.session_state.experiment_type = None

# Check if new dataset is loaded or settings that trigger re-detection change
if uploaded_file.name != st.session_state.get("current_dataset_for_type_detection") or \
   st.session_state.get("last_file") != uploaded_file.name: # Add other relevant settings if they affect file names
    st.session_state.current_dataset_for_type_detection = uploaded_file.name
    
    # Get CSV names from the zip for type detection
    # This requires a way to peek into the zip or get names from read_zip_data more directly
    # For now, let's assume read_zip_data can also return csv_names for this purpose
    # We might need to modify read_zip_data or add a helper to get names first.
    # TEMPORARY: Read zip to get names (this is inefficient as it's read again later)
    temp_csv_names = []
    with zipfile.ZipFile(uploaded_file, "r") as z_temp:
        temp_csv_names = sorted([f for f in z_temp.namelist() if f.lower().endswith("raw.csv")])
    
    if temp_csv_names:
        st.session_state.experiment_type = detect_experiment_type(temp_csv_names)
    else:
        st.session_state.experiment_type = 'screening' # Default if no CSVs

# Display detected experiment type
if st.session_state.experiment_type:
    st.sidebar.info(f"Detected Experiment Type: {st.session_state.experiment_type.replace('-', ' ').title()}")

# Process the data
# Create progress indicators
progress_bar = st.progress(0, text="Processing data...")
progress_text = st.empty()

def update_progress(current, total, capillary):
    """Update the progress bar and display current capillary"""
    progress = current / total
    progress_bar.progress(progress, text=f"Processing {current}/{total} files...")
    progress_text.text(f"Analyzing capillary: {capillary}")

# Initialize session state for caching results and experiment type
if "processed_results" not in st.session_state:
    st.session_state.processed_results = None
    st.session_state.capillary_data = None
    st.session_state.all_csv_names_in_zip = [] 
    st.session_state.experiment_type = None 
    st.session_state.last_file_for_type_detection = None # Track file for type detection

needs_reprocessing = False
if st.session_state.get("last_file") != uploaded_file.name or \
   st.session_state.get("last_channel") != channel or \
   st.session_state.get("last_method") != method or \
   st.session_state.get("last_window") != window_length or \
   st.session_state.get("last_multi_peak") != enable_multi_peak or \
   st.session_state.get("last_interpolation") != enable_interpolation or \
   st.session_state.get("last_derivative_peak_method") != derivative_peak_method_selected or \
   st.session_state.get("last_auc_method") != auc_method or \
   st.session_state.get("last_auc_baseline_correction") != auc_baseline_correction or \
   st.session_state.get("last_auc_smoothing_window") != auc_smoothing_window or \
   st.session_state.get("last_auc_interpolation_factor") != auc_interpolation_factor or \
   st.session_state.get("last_sg_poly_order") != sg_poly_order:
    needs_reprocessing = True

if needs_reprocessing:
    if st.session_state.debug_mode:
        st.session_state.global_debug_log.append("Reprocessing data...")
    df_results, capillary_data, all_csv_names = read_zip_data(
        uploaded_file, channel, method, window_length, update_progress, 
        enable_multi_peak, enable_interpolation, derivative_peak_method_selected,
        sg_poly_order=sg_poly_order, auc_method=auc_method, auc_baseline_correction=auc_baseline_correction,
        auc_smoothing_window=auc_smoothing_window, auc_interpolation_factor=auc_interpolation_factor,
        debug_mode=st.session_state.debug_mode
    )
    st.session_state.processed_results = df_results
    st.session_state.capillary_data = capillary_data
    st.session_state.all_csv_names_in_zip = all_csv_names
    # Update last processed parameters
    st.session_state.last_file = uploaded_file.name
    st.session_state.last_channel = channel
    st.session_state.last_method = method
    st.session_state.last_window = window_length
    st.session_state.last_multi_peak = enable_multi_peak
    st.session_state.last_interpolation = enable_interpolation
    st.session_state.last_derivative_peak_method = derivative_peak_method_selected
    st.session_state.last_auc_method = auc_method
    st.session_state.last_auc_baseline_correction = auc_baseline_correction
    st.session_state.last_auc_smoothing_window = auc_smoothing_window
    st.session_state.last_auc_interpolation_factor = auc_interpolation_factor
    st.session_state.last_sg_poly_order = sg_poly_order
    
    # Experiment type detection should happen if the file changed, or if it hasn't been detected yet for these csvs
    if st.session_state.all_csv_names_in_zip:
        st.session_state.experiment_type = detect_experiment_type(st.session_state.all_csv_names_in_zip)
        st.session_state.last_file_for_type_detection = uploaded_file.name # Mark that type detection was run for this file content
    elif df_results is None: # Check if read_zip_data indicated no processable files
        st.error("No raw CSV files found in the ZIP archive that match channel criteria or are processable.")
        st.session_state.experiment_type = 'screening' # Default, though data is likely unusable
        st.stop() # Stop if no data could be processed
    else:
        st.session_state.experiment_type = 'screening' # Default if no CSVs somehow, but df_results exist

    if st.session_state.debug_mode and df_results is None:
        st.session_state.global_debug_log.append("read_zip_data returned no df_results.")

elif st.session_state.get("last_file_for_type_detection") != uploaded_file.name and st.session_state.all_csv_names_in_zip:
    # This covers the case where processing parameters didn't change, but the file did (e.g. re-upload of same name but new content)
    # or if loaded from cache and type detection never ran for *this specific set* of all_csv_names_in_zip
    st.session_state.experiment_type = detect_experiment_type(st.session_state.all_csv_names_in_zip)
    st.session_state.last_file_for_type_detection = uploaded_file.name

else:
    # Use cached results if no reprocessing needed
    df_results = st.session_state.processed_results
    capillary_data = st.session_state.capillary_data
    # experiment_type should persist from session_state

# Display detected experiment type if available
if st.session_state.experiment_type:
    st.sidebar.info(f"Detected Experiment Type: {st.session_state.experiment_type.replace('-', ' ').title()}")

# Clear progress indicators 
progress_bar.empty()
progress_text.empty()

if df_results is None or df_results.empty:
    # This check is crucial after all data loading/caching logic
    st.error("No data processed. Please check the ZIP file and selected channel.")
    st.stop()

# Process multi-peak data if enabled
if enable_multi_peak:
    # Initialize columns for secondary transitions
    if "Secondary Tm (°C)" not in df_results.columns:
        df_results["Primary Tm (°C)"] = np.nan
        df_results["Secondary Tm (°C)"] = np.nan
        df_results["Primary SNR"] = np.nan
        df_results["Secondary SNR"] = np.nan
        df_results["Weighted Tm (°C)"] = np.nan
    
    # First pass: collect all transitions
    all_transitions = []
    for cap_id, data in capillary_data.items():
        # Get the primary transition
        cap_mask = df_results["Capillary"] == cap_id
        if not any(cap_mask):
            continue
            
        primary_tm = df_results.loc[cap_mask, "TM (°C)"].values[0]
        primary_snr = df_results.loc[cap_mask, "State SNR"].values[0]
        
        # Add primary transition to the list
        all_transitions.append({
            "capillary": cap_id,
            "tm": primary_tm,
            "snr": primary_snr,
            "type": "primary"
        })
        
        # Add secondary transitions if they exist
        if "additional_peaks" in data and data["additional_peaks"]:
            for peak in data["additional_peaks"]:
                all_transitions.append({
                    "capillary": cap_id,
                    "tm": peak["temp"],
                    "snr": peak["snr"],
                    "type": "secondary"
                })
    
    # Group transitions by temperature clusters if we have enough data
    if len(all_transitions) >= 3:
        # Convert to DataFrame for easier analysis
        transitions_df = pd.DataFrame(all_transitions)
        
        # Calculate median temperature to separate clusters
        all_temps = transitions_df["tm"].values
        
        # If we have a clear bimodal distribution, find the optimal separation point
        # Otherwise, use the median as a simple separator
        if len(all_temps) >= 6:  # Need enough points to detect clusters
            # Sort temperatures
            sorted_temps = np.sort(all_temps)
            
            # Look for a gap in the sorted temperatures
            temp_diffs = np.diff(sorted_temps)
            if np.max(temp_diffs) > 2.0:  # If there's a gap of at least 2°C
                # Use the midpoint of the largest gap as the separator
                gap_idx = np.argmax(temp_diffs)
                separator = (sorted_temps[gap_idx] + sorted_temps[gap_idx + 1]) / 2
            else:
                # Use the median if no clear gap
                separator = np.median(all_temps)
        else:
            # Use the median for smaller datasets
            separator = np.median(all_temps)
        
        # Classify transitions as low or high based on the separator
        transitions_df["cluster"] = transitions_df["tm"].apply(lambda x: "low" if x < separator else "high")
        
        # Process each capillary to assign and reclassify primary/secondary
        for cap_id in df_results["Capillary"].unique():
            cap_transitions = transitions_df[transitions_df["capillary"] == cap_id]
            
            if len(cap_transitions) <= 1:
                continue  # Skip if only one transition
            
            # Check if we have both low and high transitions
            has_low = any(cap_transitions["cluster"] == "low")
            has_high = any(cap_transitions["cluster"] == "high")
            
            if has_low and has_high:
                # Get the best low and high transitions by SNR
                best_low = cap_transitions[cap_transitions["cluster"] == "low"].sort_values("snr", ascending=False).iloc[0]
                best_high = cap_transitions[cap_transitions["cluster"] == "high"].sort_values("snr", ascending=False).iloc[0]
                
                # Assign as primary (low) and secondary (high) transitions
                low_tm = best_low["tm"]
                low_snr = best_low["snr"]
                high_tm = best_high["tm"]
                high_snr = best_high["snr"]
                
                # Calculate weighted average
                if not np.isnan(low_snr) and not np.isnan(high_snr) and low_snr > 0 and high_snr > 0:
                    total_snr = low_snr + high_snr
                    weighted_tm = (low_tm * low_snr + high_tm * high_snr) / total_snr
                else:
                    weighted_tm = np.nan
                
                # Update the results dataframe
                cap_mask = df_results["Capillary"] == cap_id
                if any(cap_mask):
                    df_results.loc[cap_mask, "Primary Tm (°C)"] = low_tm
                    df_results.loc[cap_mask, "Secondary Tm (°C)"] = high_tm
                    df_results.loc[cap_mask, "Primary SNR"] = low_snr
                    df_results.loc[cap_mask, "Secondary SNR"] = high_snr
                    df_results.loc[cap_mask, "Weighted Tm (°C)"] = weighted_tm
                    
                    # Also update the TM column to be the low temperature transition for consistency
                    df_results.loc[cap_mask, "TM (°C)"] = low_tm
                    df_results.loc[cap_mask, "State SNR"] = low_snr

# Apply any manually edited concentrations
if st.session_state.edited_concentrations:
    for index, row in df_results.iterrows():
        cap_id = row["Capillary"]
        if cap_id in st.session_state.edited_concentrations:
            df_results.loc[index, "Concentration"] = st.session_state.edited_concentrations[cap_id]


# Initialize checkbox states for all capillaries
for _, row in df_results.iterrows():
    if row["Capillary"] not in st.session_state.checkbox_states:
        st.session_state.checkbox_states[row["Capillary"]] = True


# Add checkbox column using preserved states
df_results["Include in EC50"] = df_results["Capillary"].map(st.session_state.checkbox_states)


# Sort the dataframe by capillary ID
try:
    df_results = df_results.sort_values("Capillary")
except:
    pass


# Reset index for display
df_display = df_results.reset_index(drop=True)


# Convert concentration to string for TextColumn compatibility
if "Concentration" in df_display.columns:
    df_display["Concentration"] = df_display["Concentration"].apply(
        lambda x: f"{x:.2e}" if pd.notnull(x) else ""
    )


# Summary table
st.header("Summary of Tm Results")
st.caption("Customize displayed columns using the 'Table Display Settings' in the sidebar")

# Filter columns based on user selection
valid_columns = [col for col in selected_columns if col in df_display.columns]
df_display_filtered = df_display[valid_columns].copy()

# Set up the table configuration
column_config = format_results_table(df_display, enable_multi_peak)
column_config_filtered = {col: column_config[col] for col in valid_columns if col in column_config}

# Display the editable table
editor_key = f"editor_{uploaded_file.name}_{channel}_{method}"
edited_df = st.data_editor(
    df_display_filtered,
    key=editor_key,
    hide_index=True,
    use_container_width=True,
    column_config=column_config_filtered
)


# Update session state with edited values
for index, row in edited_df.iterrows():
    cap_id = row["Capillary"]
    
    # Update Include in EC50 if present
    if "Include in EC50" in row:
        st.session_state.checkbox_states[cap_id] = row["Include in EC50"]
    
    # Update Concentration if present
    if "Concentration" in row:
        conc_str = str(row["Concentration"])
        if conc_str.strip() == "":
            st.session_state.edited_concentrations[cap_id] = None
        else:
            try:
                parsed_conc = float(conc_str)
                st.session_state.edited_concentrations[cap_id] = parsed_conc
            except ValueError:
                st.warning(
                    f"Invalid concentration for {cap_id}: '{conc_str}'. "
                    "Use numbers or scientific notation (e.g., 1e-7)."
                )
                if cap_id not in st.session_state.edited_concentrations:
                    st.session_state.edited_concentrations[cap_id] = None
    
    # Update Sample Info if present
    if "Sample Info" in row and "Sample Info" in df_results.columns:
        sample_info = row["Sample Info"]
        # Find the corresponding row in the full results dataframe
        mask = df_results["Capillary"] == cap_id
        if any(mask):
            df_results.loc[mask, "Sample Info"] = sample_info


# Prepare data for analysis
st.info("Fill 'Sample Info' and 'Concentration', then run EC50 or ΔTm analysis.")


# EC50 analysis section
if st.button("Calculate EC50"):
    # Create dataframe for fitting with updated concentrations
    df_fit = df_results.copy()
    
    # Update with edited concentrations
    for idx, row in df_fit.iterrows():
        cap_id = row["Capillary"]
        if cap_id in st.session_state.edited_concentrations:
            df_fit.loc[idx, "Concentration"] = st.session_state.edited_concentrations[cap_id]
    
    # Filter for selected capillaries with valid concentrations
    df_fit = df_fit[df_fit["Include in EC50"]].copy()
    df_fit["Concentration"] = pd.to_numeric(df_fit["Concentration"], errors="coerce")
    df_fit.dropna(subset=["Concentration"], inplace=True)
    
    if len(df_fit) < 3:
        st.error("Need at least 3 selected capillaries with concentration values for EC50 fitting.")
        st.stop()
    
    # Check if we need to calculate EC50 for multiple transitions
    calculate_secondary = enable_multi_peak and "Secondary Tm (°C)" in df_fit.columns and df_fit["Secondary Tm (°C)"].notna().sum() >= 3
    
    # Prepare columns for EC50 fitting
    df_fit["Primary TmToFit"] = df_fit["TM (°C)"]
    
    if calculate_secondary:
        # For secondary transition, create a valid subset
        df_fit_secondary = df_fit.dropna(subset=["Secondary Tm (°C)"]).copy()
    
    # Extract data for primary transition fitting
    x_primary = df_fit["Concentration"].astype(float).values
    y_primary = df_fit["Primary TmToFit"].values
    errors_primary = df_fit["SE (°C)"].astype(float).values
    
    # Display header based on whether we have multiple transitions
    if calculate_secondary:
        st.subheader("Primary Transition: Dose–Response Fit Results (4PL)")
    else:
        st.subheader("Dose–Response Fit Results (4PL)")
    
    # Perform EC50 analysis for primary transition
    ec50_primary, ci_primary, se_primary, r2_primary, popt_primary, pcov_primary = analyze_ec50(x_primary, y_primary)
    
    # Display results for primary transition
    st.write(f"EC50 = {ec50_primary:.2e} M (95% CI: {ci_primary[0]:.2e}–{ci_primary[1]:.2e})")
    st.write(f"R² = {r2_primary:.3f}")
    
    # Plot EC50 curve for primary transition
    fig_primary = plot_ec50_curve(x_primary, y_primary, errors_primary, popt_primary)
    st.pyplot(fig_primary)
    plt.close(fig_primary)
    
    # If we have enough data for secondary transition EC50, calculate it
    if calculate_secondary:
        # Extract data for secondary transition fitting
        x_secondary = df_fit_secondary["Concentration"].astype(float).values
        y_secondary = df_fit_secondary["Secondary Tm (°C)"].values
        errors_secondary = df_fit_secondary["SE (°C)"].astype(float).values
        
        # Secondary transition header
        st.subheader("Secondary Transition: Dose–Response Fit Results (4PL)")
        
        # Perform EC50 analysis for secondary transition
        try:
            ec50_secondary, ci_secondary, se_secondary, r2_secondary, popt_secondary, pcov_secondary = analyze_ec50(x_secondary, y_secondary)
            
            # Display results for secondary transition
            st.write(f"EC50 = {ec50_secondary:.2e} M (95% CI: {ci_secondary[0]:.2e}–{ci_secondary[1]:.2e})")
            st.write(f"R² = {r2_secondary:.3f}")
            
            # Plot EC50 curve for secondary transition
            fig_secondary = plot_ec50_curve(x_secondary, y_secondary, errors_secondary, popt_secondary)
            st.pyplot(fig_secondary)
            plt.close(fig_secondary)
        except Exception as e:
            st.error(f"Failed to calculate EC50 for secondary transition: {e}")


# Single-dose ΔTm screening section
# This section is shown if experiment_type is 'screening'
st.header("Single-Dose ΔTm Screening")
st.markdown("Select a control capillary. ΔTm will be calculated for all other capillaries **marked as included** in the summary table above.")

# Get all capillary options for the control dropdown from the original, unfiltered df_results
all_cap_options_for_control = df_results["Capillary"].unique().tolist()

if not all_cap_options_for_control:
    st.warning("No capillary data available to select a control for ΔTm.")
else:
    control_cap = st.selectbox(
        "Select control capillary", 
        all_cap_options_for_control, 
        key="delta_tm_control_selectbox_screening"
    )

    if st.button("Calculate ΔTm for All Other Included Samples", key="delta_tm_button_screening"):
        if not control_cap:
            st.warning("Please select a control capillary.")
        else:
            # Filter df_results to get only those samples marked for inclusion for this analysis
            # df_results already has the "Include in EC50" column updated from session_state
            df_included_samples = df_results[df_results["Include in EC50"] == True].copy()

            # Ensure the control capillary exists in the original df_results to get its Tm
            control_mask_original = df_results["Capillary"] == control_cap
            if not any(control_mask_original):
                st.error(f"Control capillary '{control_cap}' not found in the base data. This should not happen.")
                st.stop()
            
            t0_row_original = df_results.loc[control_mask_original]
            t0 = t0_row_original["TM (°C)"].values[0]
            s0 = t0_row_original.get("SE (°C)", pd.Series([0.0])).fillna(0.0).values[0]

            # Test capillaries are those from df_included_samples that are not the control_cap
            test_capillaries_from_included = [
                c for c in df_included_samples["Capillary"].unique().tolist() if c != control_cap
            ]

            if not test_capillaries_from_included:
                st.warning("No other *included* capillaries available to compare against the control. Please check the 'Include in EC50' column in the summary table.")
            else:
                delta_tm_rows = []
                for cap_id_test in test_capillaries_from_included:
                    # Get data for the test capillary from the df_included_samples
                    test_mask_included = df_included_samples["Capillary"] == cap_id_test
                    # Given how test_capillaries_from_included is constructed, mask should always find something
                    test_row_included = df_included_samples.loc[test_mask_included]
                    
                    tm_test = test_row_included["TM (°C)"].values[0]
                    se_test = test_row_included.get("SE (°C)", pd.Series([0.0])).fillna(0.0).values[0]
                    
                    delta_tm, se_delta = calculate_delta_tm(t0, tm_test, s0, se_test)
                    
                    sample_info_val = ""
                    # Sample Info should come from the potentially edited data in edited_df
                    # We need to ensure edited_df is used here for Sample Info consistency
                    # If this section runs before edited_df is defined in this script run, fall back to df_results
                    # (Actually, df_results has Sample Info updated from edited_df in the previous run)
                    source_df_for_sample_info = edited_df if 'edited_df' in locals() and not edited_df.empty else df_results
                    
                    info_mask_for_sample = source_df_for_sample_info["Capillary"] == cap_id_test
                    if any(info_mask_for_sample) and "Sample Info" in source_df_for_sample_info.columns:
                        sample_info_val = source_df_for_sample_info.loc[info_mask_for_sample, "Sample Info"].values[0]
                    
                    delta_tm_rows.append({
                        "Capillary": cap_id_test,
                        "Sample Info": sample_info_val if pd.notnull(sample_info_val) and sample_info_val.strip() != "" else cap_id_test,
                        "ΔTm (°C)": delta_tm,
                        "SE ΔTm (°C)": se_delta
                    })
                    
                if delta_tm_rows:
                    df_delta_screening = pd.DataFrame(delta_tm_rows).sort_values("ΔTm (°C)", ascending=False)
                    st.subheader("ΔTm Results (for Included Samples)")
                    st.dataframe(df_delta_screening, column_config={
                        "Capillary": "Capillary ID",
                        "Sample Info": "Sample Name/Info",
                        "ΔTm (°C)": st.column_config.NumberColumn("ΔTm (°C)", format="%.2f"),
                        "SE ΔTm (°C)": st.column_config.NumberColumn("SE ΔTm (°C)", format="%.2f"),
                    }, use_container_width=True, hide_index=True)
                    
                    chart_labels_screening = df_delta_screening["Sample Info"].tolist()
                    # Ensure uniqueness for labels, fallback to Capillary ID if Sample Info is not unique or empty
                    if len(set(chart_labels_screening)) != len(chart_labels_screening) or any(s == cap_id for s, cap_id in zip(chart_labels_screening, df_delta_screening["Capillary"].tolist())):
                        chart_labels_screening = df_delta_screening["Capillary"].tolist()
                        
                    fig_delta_tm_screening = plot_delta_tm(chart_labels_screening, df_delta_screening["ΔTm (°C)"].values, df_delta_screening["SE ΔTm (°C)"].values)
                    st.pyplot(fig_delta_tm_screening)
                    plt.close(fig_delta_tm_screening)
                else:
                    st.info("No ΔTm values were calculated for the included test samples.")


# Detailed per-capillary plots
st.header("Detailed Curves")
st.info("Click on a capillary to view detailed curves.")

for cap_id, data in capillary_data.items():
    with st.expander(f"Capillary {cap_id}"):
        T_raw_plot = data['T']
        F_raw_plot = data['F']
        
        if method.startswith("First derivative"):
            # Determine the correct T-axis for plotting processed data and for peak indices
            T_processed_for_plot = data.get('T_interp') if data.get('is_interpolated') else None
            T_plot_axis = T_processed_for_plot if T_processed_for_plot is not None else T_raw_plot
            
            current_smooth = data.get('smooth')
            current_deriv = data.get('deriv')

            # Determine the source for peak data for plotting
            source_for_plot_peaks = []
            if derivative_peak_method_selected == 'gaussian_deconvolution':
                # If Gaussian deconvolution was used, its results are authoritative for plotting the fit.
                source_for_plot_peaks = data.get("additional_peaks", []) # These peaks should contain 'fitted_curve'
            elif enable_multi_peak:
                # If multi-peak is enabled (and not Gaussian deconv), use additional_peaks.
                source_for_plot_peaks = data.get("additional_peaks", [])
            
            # Fallback for single peak (non-Gaussian deconv methods like find_peaks or polynomial_fit in single peak mode)
            # or if above methods yielded no peaks specifically for plotting (e.g. polynomial fit details are passed separately)
            if not source_for_plot_peaks and data.get('tm_idx') is not None and not np.isnan(data.get('tm_idx')):
                primary_idx = int(data['tm_idx'])
                if 0 <= primary_idx < len(T_plot_axis): # T_plot_axis used here
                    source_for_plot_peaks = [{
                        'idx_global': primary_idx,
                        'temp': T_plot_axis[primary_idx],
                        'snr': data.get('snr', np.nan),
                        'type': 'peak' # General peak type
                        # NO 'deconvolved' or 'fitted_curve' here for this simple fallback unless specific method adds it
                    }]
            
            all_calculated_peaks = source_for_plot_peaks # This is now the basis for 'transitions'

            # Debug for peaks for plotting
            if st.session_state.debug_mode and all_calculated_peaks:
                st.session_state.global_debug_log.append(f"[Detailed Plotting] Capillary {cap_id} - Method: {derivative_peak_method_selected}")
                st.session_state.global_debug_log.append(f"[Detailed Plotting] Capillary {cap_id} - Number of peaks for plot: {len(all_calculated_peaks)}")
                first_peak_info = all_calculated_peaks[0] if all_calculated_peaks else {}
                st.session_state.global_debug_log.append(f"[Detailed Plotting] Capillary {cap_id} - First peak for plot: temp={first_peak_info.get('temp')}, fitted_curve_present={'fitted_curve' in first_peak_info}")
                if any(p.get('fitted_curve') for p in all_calculated_peaks):
                    st.session_state.global_debug_log.append(f"[Detailed Plotting] Capillary {cap_id} - Contains 'fitted_curve' for plot: Yes")
                else:
                    st.session_state.global_debug_log.append(f"[Detailed Plotting] Capillary {cap_id} - Contains 'fitted_curve' for plot: No")

            transitions = [] # Initialize the list for peaks to plot
            # Loop to populate 'transitions' from 'all_calculated_peaks'
            # This loop correctly uses all_calculated_peaks which is populated for both multi and single (with deconv) peak modes
            for i, peak_info_from_calc in enumerate(all_calculated_peaks if all_calculated_peaks else []):
                idx_for_plot = peak_info_from_calc.get('idx_global') 
                temp_val = peak_info_from_calc.get('temp')
                
                if idx_for_plot is not None and not np.isnan(idx_for_plot):
                    idx_for_plot = int(idx_for_plot)
                    if not (0 <= idx_for_plot < len(T_plot_axis)):
                        # If index is out of bounds, try to find from temp_val if available
                        if temp_val is not None and not np.isnan(temp_val):
                            idx_for_plot = np.argmin(np.abs(T_plot_axis - temp_val))
                        else:
                            continue # Cannot plot this peak
                elif temp_val is not None and not np.isnan(temp_val):
                    idx_for_plot = np.argmin(np.abs(T_plot_axis - temp_val))
                else:
                    continue # Cannot plot this peak
                
                # Default label and color, can be overridden by peak_info_from_calc
                label = f"Tm {i+1} = {temp_val:.2f}°C" if temp_val is not None else f"Peak {i+1}"
                color = "purple"

                current_transition = {
                    'idx': idx_for_plot,
                    'temp': temp_val,
                    'label': peak_info_from_calc.get('label', label), # Use label from peak_info if present
                    'color': peak_info_from_calc.get('color', color),
                    'snr': peak_info_from_calc.get('snr'),
                    'deconvolved': peak_info_from_calc.get('deconvolved', False),
                    'amplitude': peak_info_from_calc.get('amplitude'), 
                    'width': peak_info_from_calc.get('width'),
                    'fitted_curve': peak_info_from_calc.get('fitted_curve')
                }
                transitions.append(current_transition)

            # Sort transitions by temperature for consistent labeling and plotting order
            # Ensure sorting works even if 'temp' key is missing or value is None/NaN
            transitions.sort(key=lambda x: x.get('temp', float('inf')))
            
            # Prepare polynomial fit details if the method was polynomial fit
            poly_details_for_plot = None
            if method == "First derivative" and derivative_peak_method_selected == 'polynomial_fit':
                poly_details_for_plot = data.get('details', {}) # Contains coeffs and T_window_used

            # Call plot_tm_curve for the derivative method
            figs = plot_tm_curve(
                T_raw_plot, 
                F_raw_plot,
                T_processed=T_plot_axis, 
                tm_idx=None,  # Primary Tm marking is now handled by 'additional_peaks' if it's the first item
                smooth=current_smooth,
                deriv=current_deriv,
                method="derivative",
                additional_peaks=transitions,
                polynomial_fit_details=poly_details_for_plot # Pass the details here
            )
            for fig_item in figs:
                st.pyplot(fig_item)
                plt.close(fig_item)
        
            # Display polynomial fit details if that method was used
            if derivative_peak_method_selected == 'polynomial_fit' and method == "First derivative":
                poly_details = data.get('details', {})
                r_squared = poly_details.get('polynomial_r_squared')
                coeffs = poly_details.get('polynomial_coeffs')
                st.markdown("**Polynomial Fit Details:**")
                if r_squared is not None:
                    st.metric(label="R² (Polynomial Fit)", value=f"{r_squared:.4f}")
                if coeffs is not None:
                    st.markdown(f"Coefficients (ax² + bx + c): a={coeffs[0]:.3e}, b={coeffs[1]:.3e}, c={coeffs[2]:.3e}")
                # Optionally, display the T_window_used and deriv_window_used for debugging if needed
                # T_window = poly_details.get('T_window_used')
                # deriv_window = poly_details.get('deriv_window_used')
                # if T_window:
                # st.write(f"T Window for fit: {np.min(T_window):.2f}°C to {np.max(T_window):.2f}°C")
        
        elif method == "AUC": # AUC method
            auc_result = data.get("auc_result", {})
            # For AUC, pass the auc_result as additional_peaks to the plotting function
            figs = plot_tm_curve(
                T_raw_plot, 
                F_raw_plot,
                T_processed=None, 
                method="auc",
                additional_peaks=auc_result  # Pass AUC result data for plotting
            )
            for fig_item in figs:
                st.pyplot(fig_item)
                plt.close(fig_item)
            
            # Display AUC analysis details
            if auc_result.get('success', False):
                st.markdown("**AUC Analysis Details:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    tm_auc = auc_result.get('Tm_AUC', np.nan)
                    if not np.isnan(tm_auc):
                        st.metric(label="Tm (AUC)", value=f"{tm_auc:.2f}°C")
                    
                    total_area = auc_result.get('total_area', np.nan)
                    if not np.isnan(total_area):
                        st.metric(label="Total Area", value=f"{total_area:.2f}")
                
                with col2:
                    quality_score = auc_result.get('quality_score', np.nan)
                    if not np.isnan(quality_score):
                        st.metric(label="Quality Score", value=f"{quality_score:.3f}")
                    
                    method_used = auc_result.get('method', 'Unknown')
                    st.metric(label="AUC Method", value=method_used.replace('_', ' ').title())
                
                # Method explanation
                st.info("ℹ️ **Method**: Derivative-based analysis using area under the absolute derivative curve")
                st.markdown("**Scientific Approach**:")
                st.markdown("1. 📈 Calculates derivative (dF/dT) from smoothed fluorescence data")
                st.markdown("2. 📊 Computes cumulative area under |dF/dT| curve")
                st.markdown("3. 🎯 Finds temperature where 50% of total area is reached")
                st.markdown("4. ✅ This represents the midpoint of the transition")
            else:
                # Show error if analysis failed
                error_msg = auc_result.get('error', 'Unknown error')
                st.error(f"AUC Analysis Failed: {error_msg}")
        
        else: # Boltzmann method
            popt = data.get("popt")
            # For Boltzmann, T_processed is None; plotting is on T_raw_plot
            figs = plot_tm_curve(
                T_raw_plot, 
                F_raw_plot,
                T_processed=None, 
                popt=popt,
                method="boltzmann"
            )
            for fig_item in figs:
                st.pyplot(fig_item)
                plt.close(fig_item)

st.success("Analysis complete.")

# --- Global Debug Output Area ---
if st.session_state.get("debug_mode", False):
    st.markdown("----")
    st.subheader("🐞 Global Debug Log")
    
    # 添加高斯解卷积调试信息
    if derivative_peak_method_selected == 'gaussian_deconvolution':
        st.session_state.global_debug_log.append(f"--- Gaussian Deconvolution Debug Info ---")
        st.session_state.global_debug_log.append(f"Method: {method}, Use Deconvolution: {derivative_peak_method_selected}, Multi-peak: {enable_multi_peak}")
        
        # 检查单峰模式下的解卷积情况
        deconv_caps = {}
        single_peak_with_deconv = 0
        single_peak_with_curve = 0
        
        for cap_id, data in capillary_data.items():
            if data.get('deconvolved'):
                deconv_cap_info = {
                    'has_deconv_peak': 'deconv_peak' in data,
                    'has_fitted_curve': False,
                    'peak_data': {}
                }
                
                if 'deconv_peak' in data:
                    deconv_peak = data['deconv_peak']
                    deconv_cap_info['peak_data'] = {
                        'amplitude': deconv_peak.get('amplitude'),
                        'width': deconv_peak.get('width'),
                        'has_fitted_curve': False
                    }
                    if 'fitted_curve' in deconv_peak:
                        single_peak_with_curve += 1
                        deconv_cap_info['has_fitted_curve'] = True
                
                deconv_caps[cap_id] = deconv_cap_info
                single_peak_with_deconv += 1
        
        st.session_state.global_debug_log.append(f"Found {single_peak_with_deconv} capillaries with deconvolution")
        st.session_state.global_debug_log.append(f"Capillaries with fitted curves: {single_peak_with_curve}")
        
        # 添加详细信息
        for cap_id, info in deconv_caps.items():
            keys_str = ",".join([k for k in capillary_data[cap_id].keys() if 'deconv' in k.lower()])
            st.session_state.global_debug_log.append(f"Capillary {cap_id}: has_deconv_peak={info['has_deconv_peak']}, has_fitted_curve={info['has_fitted_curve']}, deconv_keys=[{keys_str}]")
    
    if st.session_state.global_debug_log:
        log_content = "\n".join(str(item) for item in st.session_state.global_debug_log)
        st.text_area("Log Messages:", value=log_content, height=300, key="global_debug_text_area_main", disabled=True)
    else:
        st.info("No debug messages yet.") 