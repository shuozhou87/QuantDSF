#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC50 analysis module
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import t
from scipy.special import expit
from .calc import hill4, fit_4pl


def analyze_ec50(conc, response):
    """
    Analyze EC50 using 4PL fitting
    
    Parameters:
        conc (np.ndarray): Concentration array
        response (np.ndarray): Response array
        
    Returns:
        tuple: (EC50 value, confidence interval, standard error, R², optimized parameters, covariance matrix)
    """
    return fit_4pl(conc, response)


def analyze_global_fit(T, F, C, base_params_mean):
    """
    Analyze global combined fitting for EC50
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        C (np.ndarray): Concentration array
        base_params_mean (np.ndarray): Base parameters mean
        
    Returns:
        tuple: (optimized parameters, Jacobian, residuals)
    """
    # Base_params_mean: [A_N, alpha, D_N, A_D, beta, D_D, k]
    A_N0, alpha0, D_N0, A_D0, beta0, D_D0, k0 = base_params_mean
    
    # Initial parameters
    p0 = [
        A_N0, alpha0, D_N0, A_D0, beta0, D_D0, k0,  # 7 Boltzmann parameters
        65.0, 25.0, np.median(C), 1.0  # 4 EC50 model parameters
    ]
    
    # Parameter bounds
    lower_bounds = [0, 0, -np.inf, 0, 0, -np.inf, 1e-6, 0, 0, 1e-12, 0.1]
    upper_bounds = [np.inf] * 11
    
    # Clip initial parameters to bounds
    p0 = np.maximum(p0, lower_bounds)
    p0 = np.minimum(p0, upper_bounds)
    
    def residuals(params):
        """Calculate residuals for global fitting"""
        A_N, alpha, D_N, A_D, beta, D_D, k, Tm0, dTm, Kd, n = params
        F_N = A_N * np.exp(-alpha * T) + D_N
        F_D = A_D * np.exp(-beta * T) + D_D
        Tm_vals = Tm0 + dTm * (C**n) / (Kd**n + C**n)
        return F_N + (F_D - F_N) * expit((T - Tm_vals) / k) - F
    
    # Perform least squares fitting
    result = least_squares(
        residuals, 
        p0, 
        bounds=(lower_bounds, upper_bounds),
        ftol=1e-8, 
        xtol=1e-8, 
        gtol=1e-8,
        x_scale='jac', 
        max_nfev=300000
    )
    
    return result.x, result.jac, result.fun 