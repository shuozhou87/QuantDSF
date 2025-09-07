#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modular TM calculation interface
Main entry point for nanoDSF temperature analysis
"""
import numpy as np

# Import all specialized modules
from .boltzmann_fitting import boltzmann_exp, boltzmann_linear, fit_boltzmann_model
from .derivative_analysis import calc_tm_derivative, validate_derivative_result
from .auc_analysis import calc_tm_auc, calc_multi_tm_auc, compare_auc_methods
from .peak_refinement import calc_tm_polynomial_fit, refine_peak_position, group_peaks_by_proximity
from .signal_processing import apply_edge_dampening, calculate_snr, smooth_signal
from .gaussian_analysis import gaussian, multi_gaussian, deconvolute_peaks

# Re-export key functions for backward compatibility
__all__ = [
    # Boltzmann fitting
    'boltzmann_exp',
    'boltzmann_linear', 
    'fit_boltzmann_model',
    
    # Derivative analysis
    'calc_tm_derivative',
    'validate_derivative_result',
    
    # AUC analysis (NEW)
    'calc_tm_auc',
    'calc_multi_tm_auc',
    'compare_auc_methods',
    
    # Peak analysis
    'calc_tm_polynomial_fit',
    'refine_peak_position',
    'group_peaks_by_proximity',
    
    # Signal processing
    'apply_edge_dampening',
    'calculate_snr', 
    'smooth_signal',
    
    # Gaussian analysis
    'gaussian',
    'multi_gaussian',
    'deconvolute_peaks',
    
    # High-level analysis functions
    'analyze_tm_comprehensive',
    'compare_tm_methods',
    'get_method_recommendations'
]


def analyze_tm_comprehensive(T, F, methods='all', **kwargs):
    """
    Comprehensive Tm analysis using multiple methods
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        methods (str or list): Methods to use ('all', 'derivative', 'boltzmann', 'auc', or list)
        **kwargs: Method-specific parameters
    
    Returns:
        dict: Results from all requested methods with comparison
    """
    results = {}
    
    # Determine which methods to run
    if methods == 'all':
        methods_to_run = ['derivative', 'boltzmann', 'auc']
    elif isinstance(methods, str):
        methods_to_run = [methods]
    else:
        methods_to_run = methods
    
    # Extract method-specific parameters
    derivative_params = kwargs.get('derivative_params', {})
    boltzmann_params = kwargs.get('boltzmann_params', {})
    auc_params = kwargs.get('auc_params', {})
    
    # Run First Derivative method
    if 'derivative' in methods_to_run:
        try:
            window_length = derivative_params.get('window_length', 11)
            multi_peak = derivative_params.get('multi_peak_detection', False)
            use_polynomial = derivative_params.get('use_polynomial_refinement', False)
            polynomial_window = derivative_params.get('polynomial_window', 5)
            
            # Remove the explicitly handled parameters to avoid conflicts
            clean_derivative_params = derivative_params.copy()
            for param in ['window_length', 'multi_peak_detection', 'use_polynomial_refinement', 'polynomial_window']:
                clean_derivative_params.pop(param, None)
            
            deriv_result = calc_tm_derivative(
                T, F, 
                window_length=window_length,
                multi_peak_detection=multi_peak,
                use_polynomial_refinement=use_polynomial,
                polynomial_window=polynomial_window,
                **clean_derivative_params
            )
            
            if len(deriv_result) >= 5:
                tm_value, smooth_F, derivative, peak_idx, additional_peaks = deriv_result[:5]
                
                # Validate result
                validation = validate_derivative_result(T, derivative, tm_value, peak_idx)
                
                # Check if polynomial refinement was used
                poly_info = {}
                if additional_peaks and len(additional_peaks) > 0:
                    first_peak = additional_peaks[0]
                    if 'Tm_poly' in first_peak:
                        poly_info = {
                            'polynomial_used': True,
                            'Tm_poly': first_peak.get('Tm_poly'),
                            'poly_coeffs': first_peak.get('poly_coeffs'),
                            'poly_r_squared': first_peak.get('poly_r_squared'),
                            'poly_area': first_peak.get('poly_area')
                        }
                    else:
                        poly_info['polynomial_used'] = False
                else:
                    poly_info['polynomial_used'] = False
                
                results['derivative'] = {
                    'Tm': tm_value,
                    'method': 'First Derivative',
                    'smooth_signal': smooth_F,
                    'derivative_curve': derivative,
                    'peak_index': peak_idx,
                    'additional_peaks': additional_peaks,
                    'validation': validation,
                    'polynomial_info': poly_info,
                    'success': not np.isnan(tm_value)
                }
            else:
                results['derivative'] = {
                    'Tm': np.nan,
                    'method': 'First Derivative',
                    'success': False,
                    'error': 'Insufficient return values'
                }
                
        except Exception as e:
            results['derivative'] = {
                'Tm': np.nan,
                'method': 'First Derivative', 
                'success': False,
                'error': str(e)
            }
    
    # Run Two-State Boltzmann method
    if 'boltzmann' in methods_to_run:
        try:
            model_type = boltzmann_params.get('model', 'exponential')
            
            boltz_result = fit_boltzmann_model(
                T, F,
                model=model_type,
                **boltzmann_params
            )
            
            if boltz_result and boltz_result.get('success', False):
                results['boltzmann'] = {
                    'Tm': boltz_result['Tm'],
                    'method': f'Two-State Boltzmann ({model_type})',
                    'R_squared': boltz_result['R_squared'],
                    'state_snr': boltz_result.get('state_snr', np.nan),
                    'steepness': boltz_result.get('steepness', np.nan),
                    'fitted_curve': boltz_result.get('fitted_curve', []),
                    'parameters': boltz_result.get('parameters', {}),
                    'success': True
                }
            else:
                error_msg = boltz_result.get('error', 'Unknown error') if boltz_result else 'Fitting failed'
                results['boltzmann'] = {
                    'Tm': np.nan,
                    'method': f'Two-State Boltzmann ({model_type})',
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            results['boltzmann'] = {
                'Tm': np.nan,
                'method': 'Two-State Boltzmann',
                'success': False,
                'error': str(e)
            }
    
    # Run AUC method (NEW)
    if 'auc' in methods_to_run:
        try:
            auc_method = auc_params.get('method', 'derivative')
            multi_transition = auc_params.get('multi_transition', False)
            
            if multi_transition:
                auc_result = calc_multi_tm_auc(
                    T, F,
                    method=auc_method,
                    **auc_params
                )
            else:
                auc_result = calc_tm_auc(
                    T, F,
                    method=auc_method,
                    **auc_params
                )
            
            if auc_result.get('success', False):
                results['auc'] = {
                    'Tm': auc_result['Tm_AUC'],
                    'method': f'AUC ({auc_method})',
                    'total_area': auc_result.get('total_area', np.nan),
                    'quality_score': auc_result.get('quality_score', np.nan),
                    'cumulative_area': auc_result.get('cumulative_area', []),
                    'temperature_range': auc_result.get('temperature_range', []),
                    'multi_transition': auc_result.get('multi_transition', False),
                    'transition_temperatures': auc_result.get('transition_temperatures', []),
                    'success': True
                }
            else:
                error_msg = auc_result.get('error', 'Unknown error') if auc_result else 'AUC calculation failed'
                results['auc'] = {
                    'Tm': np.nan,
                    'method': f'AUC ({auc_method})',
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            results['auc'] = {
                'Tm': np.nan,
                'method': 'AUC',
                'success': False,
                'error': str(e)
            }
    
    # Add comparison and recommendations
    results['comparison'] = _compare_results(results)
    results['recommendations'] = get_method_recommendations(results)
    
    return results


def compare_tm_methods(T, F, **kwargs):
    """
    Compare all available Tm calculation methods
    
    Parameters:
        T (np.ndarray): Temperature array
        F (np.ndarray): Fluorescence array
        **kwargs: Method-specific parameters
    
    Returns:
        dict: Comprehensive comparison of all methods
    """
    # Run comprehensive analysis
    results = analyze_tm_comprehensive(T, F, methods='all', **kwargs)
    
    # Extract Tm values for comparison
    tm_values = {}
    method_quality = {}
    
    for method_name, result in results.items():
        if method_name in ['comparison', 'recommendations']:
            continue
            
        if result.get('success', False):
            tm_values[method_name] = result['Tm']
            
            # Calculate quality score based on method-specific metrics
            if method_name == 'derivative':
                quality = result.get('validation', {}).get('quality_score', 0.5)
            elif method_name == 'boltzmann':
                r_squared = result.get('R_squared', 0.0)
                quality = min(r_squared, 1.0)
            elif method_name == 'auc':
                quality = result.get('quality_score', 0.5)
            else:
                quality = 0.5
            
            method_quality[method_name] = quality
        else:
            tm_values[method_name] = np.nan
            method_quality[method_name] = 0.0
    
    # Calculate statistics
    valid_tms = [tm for tm in tm_values.values() if not np.isnan(tm)]
    
    if len(valid_tms) > 1:
        tm_std = np.std(valid_tms)
        tm_range = np.ptp(valid_tms)
        agreement = 'Good' if tm_std < 2.0 else 'Poor' if tm_std > 5.0 else 'Moderate'
    else:
        tm_std = np.nan
        tm_range = np.nan
        agreement = 'N/A'
    
    comparison_result = {
        'tm_values': tm_values,
        'method_quality': method_quality,
        'statistics': {
            'mean_tm': np.nanmean(list(tm_values.values())) if valid_tms else np.nan,
            'std_tm': tm_std,
            'range_tm': tm_range,
            'agreement': agreement,
            'num_successful_methods': len(valid_tms)
        },
        'individual_results': results
    }
    
    return comparison_result


def get_method_recommendations(results):
    """
    Get recommendations for best method based on data characteristics
    
    Parameters:
        results (dict): Results from analyze_tm_comprehensive
    
    Returns:
        dict: Method recommendations with reasoning
    """
    recommendations = {
        'primary_method': None,
        'backup_method': None,
        'reasoning': [],
        'warnings': []
    }
    
    successful_methods = {}
    for method_name, result in results.items():
        if method_name in ['comparison', 'recommendations']:
            continue
        if result.get('success', False):
            successful_methods[method_name] = result
    
    if not successful_methods:
        recommendations['primary_method'] = 'derivative'
        recommendations['reasoning'].append('No methods succeeded - default to derivative method')
        recommendations['warnings'].append('All methods failed - check data quality')
        return recommendations
    
    # Score each method
    method_scores = {}
    
    for method_name, result in successful_methods.items():
        score = 0
        
        if method_name == 'derivative':
            validation = result.get('validation', {})
            score = validation.get('quality_score', 0.5) * 100
            
            # Bonus for multi-peak capability
            if result.get('additional_peaks'):
                score += 10
                recommendations['reasoning'].append('Derivative method detected multiple peaks')
        
        elif method_name == 'boltzmann':
            r_squared = result.get('R_squared', 0.0)
            score = r_squared * 80  # R² is between 0-1
            
            # Bonus for high R²
            if r_squared > 0.95:
                score += 20
                recommendations['reasoning'].append(f'Boltzmann method shows excellent fit (R²={r_squared:.3f})')
        
        elif method_name == 'auc':
            quality = result.get('quality_score', 0.5)
            score = quality * 70
            
            # Bonus for multi-transition detection
            if result.get('multi_transition', False):
                score += 15
                recommendations['reasoning'].append('AUC method detected multiple transitions')
        
        method_scores[method_name] = score
    
    # Rank methods by score
    sorted_methods = sorted(method_scores.items(), key=lambda x: x[1], reverse=True)
    
    if len(sorted_methods) >= 1:
        recommendations['primary_method'] = sorted_methods[0][0]
    if len(sorted_methods) >= 2:
        recommendations['backup_method'] = sorted_methods[1][0]
    
    # Add specific recommendations
    if 'boltzmann' in successful_methods:
        boltz_r2 = successful_methods['boltzmann'].get('R_squared', 0)
        if boltz_r2 > 0.9:
            recommendations['reasoning'].append('High R² suggests good sigmoid transition - Boltzmann fitting recommended')
        elif boltz_r2 < 0.7:
            recommendations['warnings'].append('Low Boltzmann R² - consider derivative or AUC methods')
    
    if 'auc' in successful_methods:
        auc_quality = successful_methods['auc'].get('quality_score', 0)
        if auc_quality > 0.8:
            recommendations['reasoning'].append('High AUC quality score - robust against noise')
    
    # Check for method agreement
    tm_values = [result['Tm'] for result in successful_methods.values()]
    if len(tm_values) > 1:
        tm_std = np.std(tm_values)
        if tm_std < 1.0:
            recommendations['reasoning'].append('Good agreement between methods increases confidence')
        elif tm_std > 3.0:
            recommendations['warnings'].append('Poor agreement between methods - check data quality')
    
    return recommendations


def _compare_results(results):
    """Internal function to compare results between methods"""
    comparison = {
        'num_successful': 0,
        'tm_agreement': 'N/A',
        'best_method': None,
        'worst_method': None
    }
    
    successful_results = {}
    for method_name, result in results.items():
        if method_name in ['comparison', 'recommendations']:
            continue
        if result.get('success', False):
            successful_results[method_name] = result
    
    comparison['num_successful'] = len(successful_results)
    
    if len(successful_results) > 1:
        # Compare Tm values
        tm_values = [result['Tm'] for result in successful_results.values()]
        tm_std = np.std(tm_values)
        
        if tm_std < 1.0:
            comparison['tm_agreement'] = 'Excellent'
        elif tm_std < 2.0:
            comparison['tm_agreement'] = 'Good'
        elif tm_std < 5.0:
            comparison['tm_agreement'] = 'Moderate'
        else:
            comparison['tm_agreement'] = 'Poor'
    
    return comparison


# For backward compatibility, keep the original function names
def calc_tm_derivative_legacy(*args, **kwargs):
    """Legacy wrapper for calc_tm_derivative"""
    return calc_tm_derivative(*args, **kwargs)

def boltzmann_exp_legacy(*args, **kwargs):
    """Legacy wrapper for boltzmann_exp"""
    return boltzmann_exp(*args, **kwargs) 