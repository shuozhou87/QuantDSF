#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Data Integrity Checks
======================
数据完整性检查 (v0.9 requirement)

Validates basic data quality before QC analysis:
- Temperature axis present and monotonic
- Signal channel present and non-empty
- No NaN/Inf values
- Minimum data points requirement
"""

import numpy as np
from typing import Tuple, Optional


def check_data_integrity(
    T: np.ndarray,
    F: np.ndarray,
    min_points: int = 20
) -> Tuple[bool, Optional[str]]:
    """
    检查数据完整性

    Args:
        T: Temperature array (°C or K)
        F: Fluorescence signal array
        min_points: Minimum required data points

    Returns:
        (is_valid, reason_code): Tuple of validity and reason code if failed
    """
    # Check 1: Non-empty arrays
    if len(T) == 0 or len(F) == 0:
        return False, 'INSUFFICIENT_DATA_POINTS'

    # Check 2: Same length
    if len(T) != len(F):
        return False, 'DATA_LENGTH_MISMATCH'

    # Check 3: No NaN or Inf in temperature
    if np.any(~np.isfinite(T)):
        return False, 'TEMPERATURE_CONTAINS_NAN_OR_INF'

    # Check 4: No NaN or Inf in fluorescence
    if np.any(~np.isfinite(F)):
        return False, 'SIGNAL_CONTAINS_NAN_OR_INF'

    # Check 5: Monotonic temperature (strictly increasing)
    if not np.all(np.diff(T) > 0):
        return False, 'TEMPERATURE_NOT_MONOTONIC'

    # Check 6: Minimum points requirement
    if len(T) < min_points:
        return False, 'INSUFFICIENT_DATA_POINTS'

    # All checks passed
    return True, None


def validate_temperature_range(
    T: np.ndarray,
    expected_min: float = 273.15,  # 0°C in Kelvin
    expected_max: float = 373.15   # 100°C in Kelvin
) -> Tuple[bool, Optional[str]]:
    """
    验证温度范围合理性 (optional check)

    Args:
        T: Temperature array
        expected_min: Expected minimum temperature
        expected_max: Expected maximum temperature

    Returns:
        (is_valid, reason_code)
    """
    T_min = T.min()
    T_max = T.max()

    # Check if temperature is in reasonable range for DSF
    if T_min < expected_min or T_max > expected_max:
        return False, 'TEMPERATURE_OUT_OF_RANGE'

    # Check if temperature range is too narrow
    if (T_max - T_min) < 10.0:  # Less than 10°C/K range
        return False, 'TEMPERATURE_RANGE_TOO_NARROW'

    return True, None


def validate_signal_range(
    F: np.ndarray,
    min_dynamic_range: float = 0.01
) -> Tuple[bool, Optional[str]]:
    """
    验证信号范围合理性 (optional check)

    Args:
        F: Fluorescence signal array
        min_dynamic_range: Minimum required signal change (fraction)

    Returns:
        (is_valid, reason_code)
    """
    F_min = F.min()
    F_max = F.max()

    # Check if all values are identical or nearly identical
    signal_range = F_max - F_min
    signal_magnitude = max(abs(F_min), abs(F_max))

    if signal_magnitude > 0:
        dynamic_range = signal_range / signal_magnitude
        if dynamic_range < min_dynamic_range:
            return False, 'SIGNAL_NO_VARIATION'
    else:
        # All values are zero or near-zero
        return False, 'SIGNAL_NO_VARIATION'

    return True, None
