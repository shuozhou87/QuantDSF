#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dose-Response EC50 Analysis
============================
Tm vs Concentration 4PL fitting
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t
from typing import Dict, Tuple, Any


def hill4_tm(conc: np.ndarray, bottom: float, top: float, ec50: float, hill_slope: float) -> np.ndarray:
    """
    4-parameter logistic function for Tm vs concentration

    Args:
        conc: Concentration array (M)
        bottom: Bottom asymptote (Tm at zero concentration)
        top: Top asymptote (Tm at infinite concentration)
        ec50: EC50 value (M)
        hill_slope: Hill slope coefficient

    Returns:
        Predicted Tm values
    """
    return bottom + (top - bottom) * conc**hill_slope / (ec50**hill_slope + conc**hill_slope)


def fit_tm_ec50(
    concentrations: np.ndarray,
    tm_values: np.ndarray,
    bounds_ec50: Tuple[float, float] = (1e-12, 1e-2)
) -> Dict[str, Any]:
    """
    Fit 4PL curve to Tm vs concentration data

    Args:
        concentrations: Concentration array (M)
        tm_values: Tm values (°C)
        bounds_ec50: Valid EC50 range (M)

    Returns:
        Dictionary with fitting results
    """
    # Require at least 3 data points
    if len(concentrations) < 3:
        return {
            'success': False,
            'ec50': np.nan,
            'ec50_ci': (np.nan, np.nan),
            'ec50_se': np.nan,
            'r2': np.nan,
            'bottom': np.nan,
            'top': np.nan,
            'hill_slope': np.nan,
            'popt': None,
            'pcov': None
        }

    conc = np.asarray(concentrations, dtype=float)
    tm = np.asarray(tm_values, dtype=float)

    # Remove NaN values
    mask = np.isfinite(conc) & np.isfinite(tm) & (conc > 0)
    conc = conc[mask]
    tm = tm[mask]

    if len(conc) < 3:
        return {
            'success': False,
            'ec50': np.nan,
            'ec50_ci': (np.nan, np.nan),
            'ec50_se': np.nan,
            'r2': np.nan,
            'bottom': np.nan,
            'top': np.nan,
            'hill_slope': np.nan,
            'popt': None,
            'pcov': None
        }

    # Initial parameter guesses
    bottom0 = np.min(tm)
    top0 = np.max(tm)
    ec50_0 = np.median(conc)
    hill_slope_0 = 1.0

    p0 = [bottom0, top0, ec50_0, hill_slope_0]

    # Parameter bounds
    bounds = (
        [0.0, 0.0, bounds_ec50[0], 0.1],  # Lower bounds
        [np.inf, np.inf, bounds_ec50[1], 10.0]  # Upper bounds
    )

    # Try fitting with different initial hill slopes for robustness
    best_fit = None
    best_r2 = -np.inf
    best_pcov = None

    for h0 in [0.5, 1.0, 1.5, 2.0]:
        p0_try = [bottom0, top0, ec50_0, h0]

        try:
            popt, pcov = curve_fit(
                hill4_tm,
                conc,
                tm,
                p0=p0_try,
                bounds=bounds,
                maxfev=100000
            )

            # Calculate R²
            tm_pred = hill4_tm(conc, *popt)
            ss_tot = np.sum((tm - np.mean(tm))**2)
            ss_res = np.sum((tm - tm_pred)**2)
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

            if r2 > best_r2:
                best_r2 = r2
                best_fit = popt
                best_pcov = pcov

        except Exception:
            continue

    if best_fit is None:
        return {
            'success': False,
            'ec50': np.nan,
            'ec50_ci': (np.nan, np.nan),
            'ec50_se': np.nan,
            'r2': np.nan,
            'bottom': np.nan,
            'top': np.nan,
            'hill_slope': np.nan,
            'popt': None,
            'pcov': None
        }

    bottom, top, ec50, hill_slope = best_fit

    # Calculate EC50 confidence interval
    try:
        ec50_se = np.sqrt(np.diag(best_pcov))[2]
        dfree = len(conc) - len(best_fit)
        tval = t.ppf(0.975, max(dfree, 1))
        ec50_ci = (ec50 - tval * ec50_se, ec50 + tval * ec50_se)
    except Exception:
        ec50_se = np.nan
        ec50_ci = (np.nan, np.nan)

    return {
        'success': True,
        'ec50': float(ec50),
        'ec50_ci': (float(ec50_ci[0]), float(ec50_ci[1])),
        'ec50_se': float(ec50_se),
        'r2': float(best_r2),
        'bottom': float(bottom),
        'top': float(top),
        'hill_slope': float(hill_slope),
        'popt': best_fit,
        'pcov': best_pcov
    }
