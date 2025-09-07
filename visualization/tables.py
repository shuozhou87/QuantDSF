#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Table formatting functions for nanoDSF data
"""
import pandas as pd
import streamlit as st


def format_results_table(df, enable_multi_peak=False):
    """
    Format the results DataFrame for display in the Streamlit app
    
    Parameters:
        df (pd.DataFrame): Results DataFrame
        enable_multi_peak (bool): Whether multi-peak detection is enabled
        
    Returns:
        dict: Column configuration for Streamlit data editor
    """
    column_config = {
        "Capillary": st.column_config.TextColumn(
            "Capillary",
            help="Capillary identifier",
            width="medium"
        ),
        "TM (°C)": st.column_config.NumberColumn(
            "Tm (°C)",
            help="Melting temperature",
            format="%.2f",
            width="small"
        ),
        "CI Lower": st.column_config.NumberColumn(
            "CI Lower",
            help="Lower bound of 95% confidence interval",
            format="%.2f",
            width="small"
        ),
        "CI Upper": st.column_config.NumberColumn(
            "CI Upper",
            help="Upper bound of 95% confidence interval",
            format="%.2f",
            width="small"
        ),
        "SE (°C)": st.column_config.NumberColumn(
            "SE (°C)",
            help="Standard error",
            format="%.2f",
            width="small"
        ),
        "State SNR": st.column_config.NumberColumn(
            "State SNR",
            help="Signal-to-noise ratio of the transition",
            format="%.1f",
            width="small"
        ),
        "R²": st.column_config.NumberColumn(
            "R²",
            help="Coefficient of determination",
            format="%.3f",
            width="small"
        ),
        "log ΔAIC": st.column_config.NumberColumn(
            "log ΔAIC",
            help="Log of the difference in Akaike Information Criterion",
            format="%.2f",
            width="small"
        ),
        "Flag": st.column_config.TextColumn(
            "Flag",
            help="Quality flag",
            width="small"
        ),
        "Sample Info": st.column_config.TextColumn(
            "Sample Info",
            help="Custom sample information",
            width="medium"
        ),
        "Concentration": st.column_config.TextColumn(
            "Concentration",
            help="Sample concentration in molar units (e.g., 1e-6 for 1 µM)",
            width="medium"
        ),
        "Include in EC50": st.column_config.CheckboxColumn(
            "Include",
            help="Include in EC50 calculation",
            width="small"
        )
    }
    
    # Add columns for secondary transitions if multi-peak detection is enabled
    if enable_multi_peak:
        column_config.update({
            "Secondary Tm (°C)": st.column_config.NumberColumn(
                "Secondary Tm (°C)",
                help="Secondary melting temperature transition",
                format="%.2f",
                width="small"
            ),
            "Secondary SNR": st.column_config.NumberColumn(
                "Secondary SNR",
                help="Signal-to-noise ratio of the secondary transition",
                format="%.1f",
                width="small"
            ),
            "Weighted Tm (°C)": st.column_config.NumberColumn(
                "Weighted Tm (°C)",
                help="SNR-weighted average of primary and secondary transitions",
                format="%.2f",
                width="small"
            )
        })
    
    return column_config 