#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core calculation module for nanoDSF data analysis
"""
from .tm_calc import (
    # Boltzmann fitting
    boltzmann_exp, boltzmann_linear, fit_boltzmann_model,
    # Derivative analysis
    calc_tm_derivative, validate_derivative_result,
    # AUC analysis (NEW)
    calc_tm_auc, calc_multi_tm_auc, compare_auc_methods,
    # Peak analysis
    calc_tm_polynomial_fit, refine_peak_position, group_peaks_by_proximity,
    # Signal processing
    apply_edge_dampening, calculate_snr, smooth_signal,
    # Gaussian analysis
    gaussian, multi_gaussian, deconvolute_peaks,
    # High-level analysis functions
    analyze_tm_comprehensive, compare_tm_methods, get_method_recommendations
)
from .curve_fit import hill4, fit_4pl

__all__ = [
    # Legacy functions
    'boltzmann_exp',
    'calc_tm_derivative',
    'hill4',
    'fit_4pl',
    'calc_tm_polynomial_fit',
    
    # New modular functions
    'boltzmann_linear',
    'fit_boltzmann_model',
    'validate_derivative_result',
    
    # AUC analysis (NEW)
    'calc_tm_auc',
    'calc_multi_tm_auc', 
    'compare_auc_methods',
    
    # Peak and signal processing
    'refine_peak_position',
    'group_peaks_by_proximity',
    'apply_edge_dampening',
    'calculate_snr',
    'smooth_signal',
    
    # Gaussian analysis
    'gaussian',
    'multi_gaussian',
    'deconvolute_peaks',
    
    # High-level comprehensive analysis
    'analyze_tm_comprehensive',
    'compare_tm_methods',
    'get_method_recommendations'
] 