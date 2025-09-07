#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Screening analysis module
"""
import numpy as np
from scipy.stats import t


def calculate_delta_tm(tm_control, tm_sample, se_control, se_sample):
    """
    Calculate delta TM between control and sample
    
    Parameters:
        tm_control (float): Control TM value
        tm_sample (float): Sample TM value
        se_control (float): Control standard error
        se_sample (float): Sample standard error
        
    Returns:
        tuple: (delta TM value, standard error)
    """
    delta_tm = tm_sample - tm_control
    se_delta = np.sqrt(se_control**2 + se_sample**2)
    return delta_tm, se_delta


def filter_significant_changes(delta_tm_array, se_array, threshold=2.0):
    """
    Filter significant changes based on delta TM and standard error
    
    Parameters:
        delta_tm_array (np.ndarray): Array of delta TM values
        se_array (np.ndarray): Array of standard errors
        threshold (float): Significance threshold in standard deviations
        
    Returns:
        tuple: (significant indices, significant delta TM values, significant standard errors)
    """
    z_scores = np.abs(delta_tm_array / se_array)
    significant = z_scores > threshold
    return (
        np.where(significant)[0],
        delta_tm_array[significant],
        se_array[significant]
    )


def calculate_statistics(delta_tm_array, se_array):
    """
    Calculate statistical measures for delta TM analysis
    
    Parameters:
        delta_tm_array (np.ndarray): Array of delta TM values
        se_array (np.ndarray): Array of standard errors
        
    Returns:
        tuple: (weighted mean, weighted standard error, t-statistic, p-value)
    """
    # Calculate weights
    weights = 1 / (se_array**2)
    total_weight = np.sum(weights)
    
    # Calculate weighted mean
    weighted_mean = np.sum(delta_tm_array * weights) / total_weight
    
    # Calculate weighted standard error
    weighted_se = np.sqrt(1 / total_weight)
    
    # Calculate t-statistic and p-value
    t_stat = weighted_mean / weighted_se
    p_value = 2 * (1 - t.cdf(abs(t_stat), len(delta_tm_array) - 1))
    
    return weighted_mean, weighted_se, t_stat, p_value 