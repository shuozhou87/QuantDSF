#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quality Control Module
=======================
模块化质量控制系统

支持三个分析标签页的质量评估:
- Tab 1: Basic Analysis (Tm determination)
- Tab 2: Thermodynamic Analysis (Van't Hoff)
- Tab 3: Dose-Response Analysis (4PL fitting)
"""

from .base import QualityMetrics, QualityController
from .tm_qc import TmQualityController
from .thermo_qc import ThermodynamicQualityController
from .dose_response_qc import DoseResponseQualityController
from .config import QCSettings
from .reason_codes import (
    QCReasonCode,
    get_reason_code,
    format_reason_message,
    REASON_CODE_REGISTRY,
)
from .transition_bounds import (
    detect_transition_bounds,
    validate_window_in_transition,
    calculate_transition_width,
)

__all__ = [
    'QualityMetrics',
    'QualityController',
    'TmQualityController',
    'ThermodynamicQualityController',
    'DoseResponseQualityController',
    'QCSettings',
    'QCReasonCode',
    'get_reason_code',
    'format_reason_message',
    'REASON_CODE_REGISTRY',
    'detect_transition_bounds',
    'validate_window_in_transition',
    'calculate_transition_width',
]
