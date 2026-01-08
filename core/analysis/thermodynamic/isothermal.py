#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Isothermal Dose-Response Analysis
==================================
等温剂量响应分析

从 V1 迁移，保持核心算法不变
"""
import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, List, Tuple, Any, Optional


def four_param_logistic(
    log10_conc: np.ndarray,
    bottom: float,
    top: float,
    logEC50: float,
    hill_slope: float,
) -> np.ndarray:
    """
    4 参数 logistic (Hill) 方程
    
    Args:
        log10_conc: log10 浓度数组
        bottom: 最小响应
        top: 最大响应
        logEC50: log10(EC50)
        hill_slope: Hill 斜率
    
    Returns:
        响应值数组
    """
    return bottom + (top - bottom) / (1.0 + 10.0 ** (hill_slope * (logEC50 - log10_conc)))


def fit_4pl_ec50(
    log10_conc: np.ndarray,
    y_percent: np.ndarray,
    bounds_ec50: Tuple[float, float] = (1e-12, 1e-2)
) -> Dict[str, Any]:
    """
    拟合 4PL 获得 EC50 和 Hill 斜率
    
    Args:
        log10_conc: log10 浓度数组
        y_percent: 响应百分比 (0-100%)
        bounds_ec50: 有效 EC50 范围 (M)
    
    Returns:
        拟合结果字典
    """
    if len(np.unique(log10_conc)) < 4:
        return {
            'EC50': np.nan, 'hill_slope': np.nan, 'r2': np.nan,
            'bottom': np.nan, 'top': np.nan, 'success': False
        }
    
    y = np.asarray(y_percent, dtype=float)
    x = np.asarray(log10_conc, dtype=float)
    
    bottom0 = np.percentile(y, 5)
    top0 = np.percentile(y, 95)
    mid_idx = int(np.argmin(np.abs(y - (bottom0 + top0) / 2)))
    logEC50_0 = x[mid_idx]
    
    best_fit = None
    best_r2 = -np.inf
    
    for h0 in (0.6, 1.0, 1.4, 2.0):
        p0 = [bottom0, top0, logEC50_0, h0]
        bounds = (
            [0.0, 20.0, x.min() - 2, 0.1],
            [80.0, 120.0, x.max() + 2, 4.0]
        )
        
        try:
            popt, _ = curve_fit(
                four_param_logistic,
                x, y,
                p0=p0,
                bounds=bounds,
                maxfev=20000,
                method='trf'
            )
            
            yfit = four_param_logistic(x, *popt)
            ss_res = np.sum((y - yfit) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
            
            if r2 > best_r2:
                best_r2 = r2
                best_fit = popt
        except Exception:
            continue
    
    if best_fit is None:
        return {
            'EC50': np.nan, 'hill_slope': np.nan, 'r2': np.nan,
            'bottom': np.nan, 'top': np.nan, 'success': False
        }
    
    bottom, top, logEC50, hill = best_fit
    EC50 = 10 ** logEC50
    
    if not (bounds_ec50[0] <= EC50 <= bounds_ec50[1]):
        return {
            'EC50': float(EC50), 'hill_slope': float(hill), 'r2': float(best_r2),
            'bottom': float(bottom), 'top': float(top), 'success': False
        }
    
    return {
        'EC50': float(EC50),
        'hill_slope': float(hill),
        'r2': float(best_r2),
        'bottom': float(bottom),
        'top': float(top),
        'success': True
    }


def build_isothermal_dataset(
    curves: List[Dict[str, Any]],
    t_step: float = 0.5,
    use_4pl_fit: bool = False
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    将进度曲线插值到公共温度网格
    
    Args:
        curves: 曲线列表，每个包含 'concentration', 'T', 'progress' (0-100%)
        t_step: 温度步长 (°C)
        use_4pl_fit: 是否使用 4PL 拟合曲线
    
    Returns:
        (T_grid, concentrations, Y_folded) 元组
    """
    curves_sorted = sorted(curves, key=lambda x: x['concentration'])
    concentrations = np.array([c['concentration'] for c in curves_sorted])
    
    t_min = max(np.min(c['T']) for c in curves_sorted)
    t_max = min(np.max(c['T']) for c in curves_sorted)
    T_grid = np.arange(t_min + 0.5, t_max - 0.5 + 1e-9, t_step)
    
    Y_folded = np.zeros((len(curves_sorted), len(T_grid)), dtype=float)
    
    if use_4pl_fit:
        for i, curve in enumerate(curves_sorted):
            T_data = np.array(curve['T'])
            p_data = np.array(curve['progress'])
            
            try:
                def hill_4pl(T, bottom, top, tm, slope):
                    return bottom + (top - bottom) / (1.0 + np.exp(slope * (tm - T)))
                
                p0 = [0.0, 100.0, curve.get('Tm', np.median(T_data)), 0.3]
                bounds = ([0, 50, T_data.min(), 0.05], [50, 150, T_data.max(), 5.0])
                
                popt, _ = curve_fit(hill_4pl, T_data, p_data, p0=p0, bounds=bounds, maxfev=10000)
                
                p_unfold_fit = hill_4pl(T_grid, *popt)
                p_unfold_fit = np.clip(p_unfold_fit, 0.0, 100.0)
                f_folded = 100.0 - p_unfold_fit
                Y_folded[i, :] = f_folded
                
            except Exception:
                p_unfold_interp = np.interp(T_grid, T_data, p_data, left=np.nan, right=np.nan)
                f_folded = 100.0 - p_unfold_interp
                Y_folded[i, :] = f_folded
    else:
        for i, curve in enumerate(curves_sorted):
            p_unfold_interp = np.interp(T_grid, curve['T'], curve['progress'], left=np.nan, right=np.nan)
            f_folded = 100.0 - p_unfold_interp
            Y_folded[i, :] = f_folded
    
    return T_grid, concentrations, Y_folded


def compute_isothermal_ec50(
    T_grid: np.ndarray,
    concentrations: np.ndarray,
    Y_folded: np.ndarray,
    min_dynamic_range: float = 20.0,
    min_4pl_r2: float = 0.95
) -> List[Dict[str, Any]]:
    """
    在每个温度切片拟合 4PL 剂量响应
    
    Args:
        T_grid: 温度数组
        concentrations: 浓度数组
        Y_folded: 折叠比例矩阵 (n_conc, n_T)
        min_dynamic_range: 最小响应范围 (%)
        min_4pl_r2: 最小 R²
    
    Returns:
        等温 EC50 结果列表
    """
    log10_conc = np.log10(concentrations)
    results = []
    
    for j, T in enumerate(T_grid):
        y = Y_folded[:, j]
        
        if np.isnan(y).any():
            continue
        
        y_span = float(np.max(y) - np.min(y))
        if y_span < min_dynamic_range:
            continue
        
        y_clipped = np.clip(y, 0.0, 100.0)
        
        fit_result = fit_4pl_ec50(log10_conc, y_clipped)
        
        if not fit_result['success'] or fit_result['r2'] < min_4pl_r2:
            continue
        
        results.append({
            'temperature': float(T),
            'EC50': fit_result['EC50'],
            'hill_slope': fit_result['hill_slope'],
            'r2': fit_result['r2'],
            'bottom': fit_result['bottom'],
            'top': fit_result['top'],
            'dynamic_range': y_span,
            'n_points': len(concentrations),
            'success': True
        })
    
    return results

