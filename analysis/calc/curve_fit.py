#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Curve fitting module
"""
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t


def hill4(x, b, t, ec50, n):
    """
    4-parameter Hill equation
    
    Parameters:
        x (np.ndarray): Concentration array
        b (float): Bottom asymptote
        t (float): Top asymptote
        ec50 (float): EC50 value
        n (float): Hill slope
        
    Returns:
        np.ndarray: Fitted response values
    """
    return b + (t-b)*x**n/(ec50**n+x**n)


def fit_4pl(conc, response):
    """
    Fit four-parameter logistic curve
    
    Parameters:
        conc (np.ndarray): Concentration array
        response (np.ndarray): Response array
        
    Returns:
        tuple: (EC50 value, confidence interval, standard error, R², optimized parameters, covariance matrix)
    """
    # Initial parameters
    p0 = [
        response.min(),     # Bottom asymptote
        response.max(),     # Top asymptote
        np.median(conc),    # EC50
        1.0                 # Hill slope
    ]
    
    # Perform fitting
    try:
        popt, pcov = curve_fit(
            hill4,
            conc,
            response,
            p0=p0,
            maxfev=100000
        )
        
        # Calculate statistics
        ec50 = popt[2]
        se = np.sqrt(np.diag(pcov))[2]
        dfree = len(conc) - len(popt)
        tval = t.ppf(0.975, dfree)
        ci = (ec50 - tval*se, ec50 + tval*se)
        
        # Calculate R²
        y_pred = hill4(conc, *popt)
        ss_tot = np.sum((response - response.mean())**2)
        ss_res = np.sum((response - y_pred)**2)
        r2 = 1 - ss_res/ss_tot if ss_tot else np.nan
        
        return ec50, ci, se, r2, popt, pcov
        
    except:
        return np.nan, (np.nan, np.nan), np.nan, np.nan, None, None 