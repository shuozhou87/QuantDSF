#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Two-State Boltzmann fitting module for nanoDSF analysis
"""
import numpy as np
from scipy.optimize import curve_fit


def boltzmann_exp(T, A_N, alpha, D_N, A_D, beta, D_D, Tm, k):
    """
    Two-state Boltzmann transition model with exponential baselines
    
    Parameters:
        T (float or np.ndarray): Temperature
        A_N (float): Native state amplitude
        alpha (float): Native state exponential coefficient
        D_N (float): Native state exponential base
        A_D (float): Denatured state amplitude  
        beta (float): Denatured state exponential coefficient
        D_D (float): Denatured state exponential base
        Tm (float): Melting temperature
        k (float): Transition steepness parameter
    
    Returns:
        float or np.ndarray: Calculated fluorescence values
    """
    # Native and denatured state baselines (exponential)
    F_N = A_N * np.exp(alpha * T) + D_N
    F_D = A_D * np.exp(beta * T) + D_D
    
    # Transition probability using Boltzmann distribution
    # Using temperature difference from Tm for better numerical stability
    delta_T = T - Tm
    exp_term = np.exp(-k * delta_T)
    
    # Avoid overflow by clipping extreme values
    exp_term = np.clip(exp_term, 1e-10, 1e10)
    
    # Fraction denatured
    f_D = 1 / (1 + exp_term)
    
    # Total fluorescence as weighted average
    F_total = (1 - f_D) * F_N + f_D * F_D
    
    return F_total


def boltzmann_linear(T, A_N, B_N, A_D, B_D, Tm, k):
    """
    Two-state Boltzmann transition model with linear baselines
    
    Parameters:
        T (float or np.ndarray): Temperature
        A_N (float): Native state slope
        B_N (float): Native state intercept
        A_D (float): Denatured state slope
        B_D (float): Denatured state intercept
        Tm (float): Melting temperature
        k (float): Transition steepness parameter
    
    Returns:
        float or np.ndarray: Calculated fluorescence values
    """
    # Native and denatured state baselines (linear)
    F_N = A_N * T + B_N
    F_D = A_D * T + B_D
    
    # Transition probability
    delta_T = T - Tm
    exp_term = np.exp(-k * delta_T)
    exp_term = np.clip(exp_term, 1e-10, 1e10)
    
    # Fraction denatured
    f_D = 1 / (1 + exp_term)
    
    # Total fluorescence as weighted average
    F_total = (1 - f_D) * F_N + f_D * F_D
    
    return F_total


def fit_boltzmann_model(T, F, model='exponential', initial_guess=None, bounds=None):
    """
    Fit Two-State Boltzmann model to fluorescence data
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        model (str): 'exponential' or 'linear' baseline model
        initial_guess (list): Initial parameter guess
        bounds (tuple): Parameter bounds (lower_bounds, upper_bounds)
    
    Returns:
        dict: Fitting results including parameters, Tm, R², and fit quality metrics
    """
    if len(T) != len(F) or len(T) < 8:
        return None
    
    # Remove any NaN or infinite values
    valid_mask = np.isfinite(T) & np.isfinite(F)
    T_clean = T[valid_mask]
    F_clean = F[valid_mask]
    
    if len(T_clean) < 8:
        return None
    
    try:
        if model == 'exponential':
            return _fit_exponential_model(T_clean, F_clean, initial_guess, bounds)
        elif model == 'linear':
            return _fit_linear_model(T_clean, F_clean, initial_guess, bounds)
        else:
            raise ValueError(f"Unknown model type: {model}")
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'Tm': np.nan,
            'R_squared': 0.0,
            'parameters': {},
            'fitted_curve': np.full_like(F, np.nan)
        }


def _fit_exponential_model(T, F, initial_guess=None, bounds=None):
    """Fit exponential baseline Boltzmann model"""
    
    # Generate initial guess if not provided
    if initial_guess is None:
        initial_guess = _generate_exp_initial_guess(T, F)
    
    # Set default bounds if not provided
    if bounds is None:
        bounds = _generate_exp_bounds(T, F)
    
    # Perform the fit
    popt, pcov = curve_fit(
        boltzmann_exp, T, F,
        p0=initial_guess,
        bounds=bounds,
        maxfev=5000
    )
    
    # Extract parameters
    A_N, alpha, D_N, A_D, beta, D_D, Tm, k = popt
    
    # Calculate fitted curve and R²
    F_fitted = boltzmann_exp(T, *popt)
    r_squared = _calculate_r_squared(F, F_fitted)
    
    # Calculate state SNR
    residuals = F - F_fitted
    rss = np.sum(residuals**2)
    degrees_freedom = len(T) - len(popt)
    sigma_resid = np.sqrt(rss / degrees_freedom) if degrees_freedom > 0 else np.nan
    
    # Calculate native and denatured state fluorescence at Tm
    F_N_at_Tm = A_N * np.exp(alpha * Tm) + D_N
    F_D_at_Tm = A_D * np.exp(beta * Tm) + D_D
    deltaF = abs(F_D_at_Tm - F_N_at_Tm)
    state_snr = deltaF / sigma_resid if sigma_resid > 0 else np.nan
    
    # Calculate parameter uncertainties
    param_std = np.sqrt(np.diag(pcov))
    
    return {
        'success': True,
        'Tm': Tm,
        'Tm_std': param_std[6],  # Standard error of Tm
        'R_squared': r_squared,
        'state_snr': state_snr,
        'steepness': k,
        'steepness_std': param_std[7],
        'parameters': {
            'A_N': A_N, 'alpha': alpha, 'D_N': D_N,
            'A_D': A_D, 'beta': beta, 'D_D': D_D,
            'Tm': Tm, 'k': k
        },
        'parameter_std': {
            'A_N': param_std[0], 'alpha': param_std[1], 'D_N': param_std[2],
            'A_D': param_std[3], 'beta': param_std[4], 'D_D': param_std[5],
            'Tm': param_std[6], 'k': param_std[7]
        },
        'fitted_curve': F_fitted,
        'covariance_matrix': pcov
    }


def _fit_linear_model(T, F, initial_guess=None, bounds=None):
    """Fit linear baseline Boltzmann model"""
    
    # Generate initial guess if not provided
    if initial_guess is None:
        initial_guess = _generate_linear_initial_guess(T, F)
    
    # Set default bounds if not provided
    if bounds is None:
        bounds = _generate_linear_bounds(T, F)
    
    # Perform the fit
    popt, pcov = curve_fit(
        boltzmann_linear, T, F,
        p0=initial_guess,
        bounds=bounds,
        maxfev=5000
    )
    
    # Extract parameters
    A_N, B_N, A_D, B_D, Tm, k = popt
    
    # Calculate fitted curve and R²
    F_fitted = boltzmann_linear(T, *popt)
    r_squared = _calculate_r_squared(F, F_fitted)
    
    # Calculate state SNR
    residuals = F - F_fitted
    rss = np.sum(residuals**2)
    degrees_freedom = len(T) - len(popt)
    sigma_resid = np.sqrt(rss / degrees_freedom) if degrees_freedom > 0 else np.nan
    
    # Calculate native and denatured state fluorescence at Tm
    F_N_at_Tm = A_N * Tm + B_N
    F_D_at_Tm = A_D * Tm + B_D
    deltaF = abs(F_D_at_Tm - F_N_at_Tm)
    state_snr = deltaF / sigma_resid if sigma_resid > 0 else np.nan
    
    # Calculate parameter uncertainties
    param_std = np.sqrt(np.diag(pcov))
    
    return {
        'success': True,
        'Tm': Tm,
        'Tm_std': param_std[4],  # Standard error of Tm
        'R_squared': r_squared,
        'state_snr': state_snr,
        'steepness': k,
        'steepness_std': param_std[5],
        'parameters': {
            'A_N': A_N, 'B_N': B_N,
            'A_D': A_D, 'B_D': B_D,
            'Tm': Tm, 'k': k
        },
        'parameter_std': {
            'A_N': param_std[0], 'B_N': param_std[1],
            'A_D': param_std[2], 'B_D': param_std[3],
            'Tm': param_std[4], 'k': param_std[5]
        },
        'fitted_curve': F_fitted,
        'covariance_matrix': pcov
    }


def _generate_exp_initial_guess(T, F):
    """Generate initial parameter guess for exponential model"""
    T_min, T_max = T.min(), T.max()
    F_min, F_max = F.min(), F.max()
    
    # Estimate Tm as temperature at midpoint fluorescence
    F_mid = (F_min + F_max) / 2
    Tm_idx = np.argmin(np.abs(F - F_mid))
    Tm_guess = T[Tm_idx]
    
    # Estimate steepness (typical range for proteins)
    k_guess = 0.1
    
    # Estimate baselines
    # Native state (low temperature, assuming first 20% of data)
    n_points = max(5, len(T) // 5)
    T_native = T[:n_points]
    F_native = F[:n_points]
    
    # Denatured state (high temperature, last 20% of data)
    T_denat = T[-n_points:]
    F_denat = F[-n_points:]
    
    # Simple exponential fit estimates
    A_N_guess = 0.0  # Small exponential component
    alpha_guess = 0.001
    D_N_guess = np.mean(F_native)
    
    A_D_guess = 0.0
    beta_guess = 0.001  
    D_D_guess = np.mean(F_denat)
    
    return [A_N_guess, alpha_guess, D_N_guess, A_D_guess, beta_guess, D_D_guess, Tm_guess, k_guess]


def _generate_linear_initial_guess(T, F):
    """Generate initial parameter guess for linear model"""
    T_min, T_max = T.min(), T.max()
    F_min, F_max = F.min(), F.max()
    
    # Estimate Tm as temperature at midpoint fluorescence
    F_mid = (F_min + F_max) / 2
    Tm_idx = np.argmin(np.abs(F - F_mid))
    Tm_guess = T[Tm_idx]
    
    # Estimate steepness
    k_guess = 0.1
    
    # Estimate linear baselines using first and last portions
    n_points = max(5, len(T) // 5)
    
    # Native state linear fit
    T_native = T[:n_points]
    F_native = F[:n_points]
    if len(T_native) > 1:
        A_N_guess = (F_native[-1] - F_native[0]) / (T_native[-1] - T_native[0])
        B_N_guess = F_native[0] - A_N_guess * T_native[0]
    else:
        A_N_guess = 0.0
        B_N_guess = F_native[0]
    
    # Denatured state linear fit
    T_denat = T[-n_points:]
    F_denat = F[-n_points:]
    if len(T_denat) > 1:
        A_D_guess = (F_denat[-1] - F_denat[0]) / (T_denat[-1] - T_denat[0])
        B_D_guess = F_denat[0] - A_D_guess * T_denat[0]
    else:
        A_D_guess = 0.0
        B_D_guess = F_denat[0]
    
    return [A_N_guess, B_N_guess, A_D_guess, B_D_guess, Tm_guess, k_guess]


def _generate_exp_bounds(T, F):
    """Generate parameter bounds for exponential model"""
    T_min, T_max = T.min(), T.max()
    F_min, F_max = F.min(), F.max()
    F_range = F_max - F_min
    
    lower_bounds = [
        -F_range, -0.1, F_min - F_range,  # A_N, alpha, D_N
        -F_range, -0.1, F_min - F_range,  # A_D, beta, D_D  
        T_min - 10, 0.01                  # Tm, k
    ]
    
    upper_bounds = [
        F_range, 0.1, F_max + F_range,    # A_N, alpha, D_N
        F_range, 0.1, F_max + F_range,    # A_D, beta, D_D
        T_max + 10, 1.0                   # Tm, k
    ]
    
    return (lower_bounds, upper_bounds)


def _generate_linear_bounds(T, F):
    """Generate parameter bounds for linear model"""
    T_min, T_max = T.min(), T.max()
    F_min, F_max = F.min(), F.max()
    F_range = F_max - F_min
    T_range = T_max - T_min
    
    max_slope = F_range / T_range * 2  # Allow some flexibility
    
    lower_bounds = [
        -max_slope, F_min - F_range,      # A_N, B_N
        -max_slope, F_min - F_range,      # A_D, B_D
        T_min - 10, 0.01                  # Tm, k
    ]
    
    upper_bounds = [
        max_slope, F_max + F_range,       # A_N, B_N
        max_slope, F_max + F_range,       # A_D, B_D
        T_max + 10, 1.0                   # Tm, k
    ]
    
    return (lower_bounds, upper_bounds)


def _calculate_r_squared(y_true, y_pred):
    """Calculate R² (coefficient of determination)"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    
    if ss_tot == 0:
        return 1.0 if ss_res < 1e-10 else 0.0
    
    return 1 - (ss_res / ss_tot) 