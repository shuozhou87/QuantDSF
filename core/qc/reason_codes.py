#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QC Reason Codes
================
Standardized machine-readable QC reason codes for QuantDSF

Following v0.9 guidelines for consistent QC reporting and export.
"""

from typing import Dict, Optional
from pydantic import BaseModel


class QCReasonCode(BaseModel):
    """QC原因代码"""
    code: str
    display_name: str
    description: str
    recommended_action: Optional[str] = None


# ==================== Data Integrity Checks (v0.9) ====================

DATA_LENGTH_MISMATCH = QCReasonCode(
    code="DATA_LENGTH_MISMATCH",
    display_name="Data Length Mismatch",
    description="Temperature and fluorescence arrays have different lengths.",
    recommended_action="Check data acquisition. Ensure temperature and signal arrays are properly aligned."
)

TEMPERATURE_CONTAINS_NAN_OR_INF = QCReasonCode(
    code="TEMPERATURE_CONTAINS_NAN_OR_INF",
    display_name="Invalid Temperature Values",
    description="Temperature array contains NaN or Inf values.",
    recommended_action="Check data acquisition. Replace or remove invalid temperature readings."
)

SIGNAL_CONTAINS_NAN_OR_INF = QCReasonCode(
    code="SIGNAL_CONTAINS_NAN_OR_INF",
    display_name="Invalid Signal Values",
    description="Fluorescence signal contains NaN or Inf values.",
    recommended_action="Check detector settings. Replace or interpolate invalid signal readings."
)

TEMPERATURE_NOT_MONOTONIC = QCReasonCode(
    code="TEMPERATURE_NOT_MONOTONIC",
    display_name="Temperature Not Monotonic",
    description="Temperature does not increase monotonically (required for thermal ramp analysis).",
    recommended_action="Check data acquisition. Ensure proper temperature ramp without cooling cycles."
)

# ==================== Tab 1: Basic Analysis Reason Codes ====================

BASELINE_UNSTABLE = QCReasonCode(
    code="BASELINE_UNSTABLE",
    display_name="Baseline Unstable",
    description="Baseline shows excessive jitter or erratic fluctuation before transition.",
    recommended_action="Check for instrument noise, bubbles, or sample issues. Consider different fluorescence channel."
)

NO_TRANSITION_DETECTED = QCReasonCode(
    code="NO_TRANSITION_DETECTED",
    display_name="No Transition Detected",
    description="No credible thermal transition could be identified in the data.",
    recommended_action="Verify sample contains protein. Check temperature range covers expected Tm. Try different channel (330nm vs 350nm)."
)

INSUFFICIENT_DATA_POINTS = QCReasonCode(
    code="INSUFFICIENT_DATA_POINTS",
    display_name="Insufficient Data Points",
    description="Too few data points for reliable analysis.",
    recommended_action="Check for data acquisition issues. Ensure full temperature ramp was recorded."
)

LOW_FIT_QUALITY = QCReasonCode(
    code="LOW_FIT_QUALITY",
    display_name="Low Fit Quality",
    description="R² below acceptable threshold, indicating poor fit to model.",
    recommended_action="Try different analysis method (TSB/AUC/FD). Check for multiphasic transitions or aggregation artifacts."
)

LOW_STATE_SNR = QCReasonCode(
    code="LOW_STATE_SNR",
    display_name="Low State SNR",
    description="Poorly defined native and denatured states relative to fitting noise.",
    recommended_action="Improve signal quality. Check protein concentration. Consider different fluorescence channel."
)

INSUFFICIENT_MODEL_SUPPORT = QCReasonCode(
    code="INSUFFICIENT_MODEL_SUPPORT",
    display_name="Insufficient Model Support",
    description="ΔAIC/ΔBIC too low: transition too simple for TSB model, or TSB overfitting noise.",
    recommended_action="Use simpler analysis method (AUC or First Derivative) instead of TSB."
)

HIGH_TM_UNCERTAINTY = QCReasonCode(
    code="HIGH_TM_UNCERTAINTY",
    display_name="High Tm Uncertainty",
    description="Tm error exceeds acceptable threshold.",
    recommended_action="Improve data quality. Check for noisy baselines or poorly defined transition."
)

LOW_DYNAMIC_RANGE = QCReasonCode(
    code="LOW_DYNAMIC_RANGE",
    display_name="Low Dynamic Range",
    description="Insufficient signal change between native and denatured states.",
    recommended_action="Check protein concentration. Try different fluorescence channel. Verify protein unfolds under experimental conditions."
)

LOW_PEAK_SNR = QCReasonCode(
    code="LOW_PEAK_SNR",
    display_name="Low Peak SNR",
    description="First derivative peak has poor signal-to-noise ratio.",
    recommended_action="Reduce smoothing to preserve peak. Check for noisy baselines. Consider TSB or AUC method instead."
)

MODEL_MISMATCH_MULTIPEAK = QCReasonCode(
    code="MODEL_MISMATCH_MULTIPEAK",
    display_name="Multiple Peaks Detected",
    description="Multiple transitions detected; simple two-state model may not be appropriate.",
    recommended_action="Consider multi-domain protein or aggregation. Analyze each transition separately if possible."
)

# ==================== Tab 2: Thermodynamic Analysis Reason Codes ====================

INSUFFICIENT_SLICING_POINTS = QCReasonCode(
    code="INSUFFICIENT_SLICING_POINTS",
    display_name="Insufficient Slicing Points",
    description="Number of temperature slices below minimum required (N < 5).",
    recommended_action="Increase slicing density or expand temperature window to include more data points."
)

WINDOW_OUTSIDE_TRANSITION = QCReasonCode(
    code="WINDOW_OUTSIDE_TRANSITION",
    display_name="Window Outside Transition",
    description="Selected temperature window is outside the plausible transition region.",
    recommended_action="Move window to be centered around Tm. Ensure window is within [onset, offset] bounds."
)

INSUFFICIENT_CONCENTRATION_RANGE = QCReasonCode(
    code="INSUFFICIENT_CONCENTRATION_RANGE",
    display_name="Insufficient Concentration Range",
    description="Temperature range (ΔT) too narrow for reliable Van't Hoff analysis.",
    recommended_action="Expand concentration range to achieve wider Tm range (≥10K recommended)."
)

LOW_VH_FIT_QUALITY = QCReasonCode(
    code="LOW_VH_FIT_QUALITY",
    display_name="Low Van't Hoff Fit Quality",
    description="R² of Van't Hoff linear regression below acceptable threshold.",
    recommended_action="Check for outliers. Verify Tm values are reliable. May indicate non-two-state behavior."
)

THERMODYNAMIC_PARAMETER_OUT_OF_RANGE = QCReasonCode(
    code="THERMODYNAMIC_PARAMETER_OUT_OF_RANGE",
    display_name="Thermodynamic Parameter Out of Range",
    description="ΔH or ΔS outside plausible physical range for protein unfolding.",
    recommended_action="Check Van't Hoff regression quality. Verify concentration units. May indicate incorrect model."
)

EXTRAPOLATED_KD = QCReasonCode(
    code="EXTRAPOLATED_KD",
    display_name="Extrapolated KD",
    description="KD prediction requires extrapolation beyond experimental concentration range.",
    recommended_action="Expand concentration range to include target temperature. Use with caution; reliability reduced."
)

# ==================== Tab 3: Dose-Response Reason Codes ====================

INSUFFICIENT_RESPONSE_COVERAGE = QCReasonCode(
    code="INSUFFICIENT_RESPONSE_COVERAGE",
    display_name="Insufficient Response Coverage",
    description="Dataset does not cover enough of the response transition (< 60% coverage).",
    recommended_action="Expand concentration range to reach both plateaus. Increase concentration span by at least 2 orders of magnitude."
)

INSUFFICIENT_CONCENTRATION_POINTS = QCReasonCode(
    code="INSUFFICIENT_CONCENTRATION_POINTS",
    display_name="Insufficient Concentration Points",
    description="Too few concentration points for reliable 4PL fitting (< 6 recommended).",
    recommended_action="Add more concentration points, especially near EC50. Use at least 6-8 concentrations."
)

FIT_NONCONVERGENCE = QCReasonCode(
    code="FIT_NONCONVERGENCE",
    display_name="Fit Non-Convergence",
    description="4PL curve fitting failed to converge to a solution.",
    recommended_action="Check data quality. Verify concentration range covers transition. Try different initial parameters."
)

IMPLAUSIBLE_HILL_SLOPE = QCReasonCode(
    code="IMPLAUSIBLE_HILL_SLOPE",
    display_name="Implausible Hill Slope",
    description="Hill slope outside typical range (0.5-4.0), suggesting unusual binding or fit issues.",
    recommended_action="Check for data quality issues. Verify experimental setup. May indicate cooperative binding or aggregation."
)

EC50_OUTSIDE_RANGE = QCReasonCode(
    code="EC50_OUTSIDE_RANGE",
    display_name="EC50 Outside Concentration Range",
    description="Fitted EC50 is outside the experimental concentration range (extrapolated).",
    recommended_action="Expand concentration range to bracket EC50. Reduce reliability weight for extrapolated values."
)


# ==================== Reason Code Registry ====================

REASON_CODE_REGISTRY: Dict[str, QCReasonCode] = {
    # Data Integrity
    "DATA_LENGTH_MISMATCH": DATA_LENGTH_MISMATCH,
    "TEMPERATURE_CONTAINS_NAN_OR_INF": TEMPERATURE_CONTAINS_NAN_OR_INF,
    "SIGNAL_CONTAINS_NAN_OR_INF": SIGNAL_CONTAINS_NAN_OR_INF,
    "TEMPERATURE_NOT_MONOTONIC": TEMPERATURE_NOT_MONOTONIC,

    # Tab 1
    "BASELINE_UNSTABLE": BASELINE_UNSTABLE,
    "NO_TRANSITION_DETECTED": NO_TRANSITION_DETECTED,
    "INSUFFICIENT_DATA_POINTS": INSUFFICIENT_DATA_POINTS,
    "LOW_FIT_QUALITY": LOW_FIT_QUALITY,
    "LOW_STATE_SNR": LOW_STATE_SNR,
    "INSUFFICIENT_MODEL_SUPPORT": INSUFFICIENT_MODEL_SUPPORT,
    "HIGH_TM_UNCERTAINTY": HIGH_TM_UNCERTAINTY,
    "LOW_DYNAMIC_RANGE": LOW_DYNAMIC_RANGE,
    "LOW_PEAK_SNR": LOW_PEAK_SNR,
    "MODEL_MISMATCH_MULTIPEAK": MODEL_MISMATCH_MULTIPEAK,

    # Tab 2
    "INSUFFICIENT_SLICING_POINTS": INSUFFICIENT_SLICING_POINTS,
    "WINDOW_OUTSIDE_TRANSITION": WINDOW_OUTSIDE_TRANSITION,
    "INSUFFICIENT_CONCENTRATION_RANGE": INSUFFICIENT_CONCENTRATION_RANGE,
    "LOW_VH_FIT_QUALITY": LOW_VH_FIT_QUALITY,
    "THERMODYNAMIC_PARAMETER_OUT_OF_RANGE": THERMODYNAMIC_PARAMETER_OUT_OF_RANGE,
    "EXTRAPOLATED_KD": EXTRAPOLATED_KD,

    # Tab 3
    "INSUFFICIENT_RESPONSE_COVERAGE": INSUFFICIENT_RESPONSE_COVERAGE,
    "INSUFFICIENT_CONCENTRATION_POINTS": INSUFFICIENT_CONCENTRATION_POINTS,
    "FIT_NONCONVERGENCE": FIT_NONCONVERGENCE,
    "IMPLAUSIBLE_HILL_SLOPE": IMPLAUSIBLE_HILL_SLOPE,
    "EC50_OUTSIDE_RANGE": EC50_OUTSIDE_RANGE,
}


def get_reason_code(code: str) -> Optional[QCReasonCode]:
    """
    获取原因代码对象

    Args:
        code: 原因代码字符串

    Returns:
        QCReasonCode对象,如果代码不存在则返回None
    """
    return REASON_CODE_REGISTRY.get(code)


def format_reason_message(code: str, include_action: bool = False) -> str:
    """
    格式化原因代码为人类可读消息

    Args:
        code: 原因代码字符串
        include_action: 是否包含推荐行动

    Returns:
        格式化的消息字符串
    """
    reason = get_reason_code(code)
    if reason is None:
        return f"Unknown reason: {code}"

    message = f"{reason.display_name}: {reason.description}"

    if include_action and reason.recommended_action:
        message += f" → {reason.recommended_action}"

    return message
