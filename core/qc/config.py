#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quality Control Configuration
===============================
QC阈值配置
"""

from pydantic import BaseModel, Field


class QCSettings(BaseModel):
    """QC阈值配置"""

    # ==================== Tab 1: Tm QC ====================

    # Universal thresholds
    min_data_points: int = Field(
        10,
        description="最少数据点数"
    )

    min_temperature_range: float = Field(
        20.0,
        description="最小温度范围 (°C)"
    )

    # TSB thresholds
    tm_r2_excellent: float = Field(
        0.95,
        description="TSB R² 优秀阈值"
    )

    tm_r2_good: float = Field(
        0.90,
        description="TSB R² 良好阈值"
    )

    tm_r2_marginal: float = Field(
        0.80,
        description="TSB R² 可接受阈值"
    )

    tm_state_snr_excellent: float = Field(
        10.0,
        description="State SNR 优秀阈值 (≥10绿标)"
    )

    tm_state_snr_marginal: float = Field(
        3.0,
        description="State SNR 可接受阈值 (3-10黄标, <3红标)"
    )

    tm_delta_aic_strong: float = Field(
        2.0,
        description="ΔAIC 强烈支持TSB阈值 (log10 scale)"
    )

    tm_delta_aic_preferred: float = Field(
        1.0,
        description="ΔAIC 支持TSB阈值 (log10 scale)"
    )

    tm_delta_aic_marginal: float = Field(
        0.5,
        description="ΔAIC 轻微支持TSB阈值 (log10 scale)"
    )

    tm_delta_bic_strong: float = Field(
        2.0,
        description="ΔBIC 强烈支持TSB阈值 (log10 scale)"
    )

    tm_delta_bic_preferred: float = Field(
        1.0,
        description="ΔBIC 支持TSB阈值 (log10 scale)"
    )

    tm_delta_bic_marginal: float = Field(
        0.5,
        description="ΔBIC 轻微支持TSB阈值 (log10 scale)"
    )

    tm_error_excellent: float = Field(
        0.3,
        description="Tm误差 优秀阈值 (°C)"
    )

    tm_error_good: float = Field(
        0.5,
        description="Tm误差 良好阈值 (°C)"
    )

    tm_error_marginal: float = Field(
        1.0,
        description="Tm误差 可接受阈值 (°C)"
    )

    # AUC thresholds (same as TSB for R²)
    auc_dynamic_range_excellent: float = Field(
        60.0,
        description="AUC动态范围 优秀阈值 (≥60%绿标)"
    )

    auc_dynamic_range_good: float = Field(
        30.0,
        description="AUC动态范围 良好阈值 (30-60%黄标)"
    )

    auc_dynamic_range_marginal: float = Field(
        30.0,
        description="AUC动态范围 可接受阈值 (<30%红标)"
    )

    # FD thresholds
    fd_peak_snr_excellent: float = Field(
        10.0,
        description="FD Peak SNR 优秀阈值 (≥10绿标)"
    )

    fd_peak_snr_marginal: float = Field(
        3.0,
        description="FD Peak SNR 可接受阈值 (3-10黄标, <3红标)"
    )

    # ==================== Tab 2: Thermodynamic QC ====================

    thermo_r2_excellent: float = Field(
        0.95,
        description="Van't Hoff R² 优秀阈值"
    )

    thermo_r2_good: float = Field(
        0.90,
        description="Van't Hoff R² 良好阈值"
    )

    thermo_r2_marginal: float = Field(
        0.85,
        description="Van't Hoff R² 可接受阈值"
    )

    thermo_min_points_excellent: int = Field(
        5,
        description="Van't Hoff 优秀数据点数"
    )

    thermo_min_points_good: int = Field(
        4,
        description="Van't Hoff 良好数据点数"
    )

    thermo_min_points_acceptable: int = Field(
        3,
        description="Van't Hoff 可接受数据点数"
    )

    thermo_min_delta_T_excellent: float = Field(
        15.0,
        description="Van't Hoff 优秀温度范围 (K)"
    )

    thermo_min_delta_T_good: float = Field(
        10.0,
        description="Van't Hoff 良好温度范围 (K)"
    )

    thermo_delta_h_min: float = Field(
        -1200.0,
        description="ΔH 最小值 (kJ/mol)"
    )

    thermo_delta_h_max: float = Field(
        0.0,
        description="ΔH 最大值 (kJ/mol)"
    )

    thermo_delta_h_typical_min: float = Field(
        -800.0,
        description="ΔH 典型最小值 (kJ/mol)"
    )

    thermo_delta_h_typical_max: float = Field(
        -50.0,
        description="ΔH 典型最大值 (kJ/mol)"
    )

    # ==================== Tab 3: Dose-Response QC ====================

    dr_r2_excellent: float = Field(
        0.95,
        description="4PL R² 优秀阈值"
    )

    dr_r2_good: float = Field(
        0.90,
        description="4PL R² 良好阈值"
    )

    dr_r2_marginal: float = Field(
        0.85,
        description="4PL R² 可接受阈值"
    )

    dr_dynamic_range_excellent: float = Field(
        60.0,
        description="数据覆盖率 优秀阈值 (%, ≥60%绿标, 实验数据覆盖拟合动态范围的比例)"
    )

    dr_dynamic_range_good: float = Field(
        30.0,
        description="数据覆盖率 良好阈值 (%, 30-60%黄标)"
    )

    dr_dynamic_range_marginal: float = Field(
        30.0,
        description="数据覆盖率 可接受阈值 (%, ≥30%可接受, <30%红标)"
    )

    dr_data_coverage_excellent: float = Field(
        60.0,
        description="数据覆盖率 优秀阈值 (%, ≥60%绿标) - 同dynamic_range"
    )

    dr_data_coverage_good: float = Field(
        30.0,
        description="数据覆盖率 良好阈值 (%, 30-60%黄标) - 同dynamic_range"
    )

    dr_data_coverage_marginal: float = Field(
        30.0,
        description="数据覆盖率 可接受阈值 (%, ≥30%可接受) - 同dynamic_range"
    )

    dr_hill_slope_min_normal: float = Field(
        0.8,
        description="Hill斜率 正常最小值"
    )

    dr_hill_slope_max_normal: float = Field(
        2.0,
        description="Hill斜率 正常最大值"
    )

    dr_hill_slope_min_acceptable: float = Field(
        0.5,
        description="Hill斜率 可接受最小值"
    )

    dr_hill_slope_max_acceptable: float = Field(
        3.0,
        description="Hill斜率 可接受最大值"
    )

    dr_min_concentrations_excellent: int = Field(
        8,
        description="浓度点数 优秀阈值"
    )

    dr_min_concentrations_good: int = Field(
        6,
        description="浓度点数 良好阈值"
    )

    dr_min_concentrations_marginal: int = Field(
        4,
        description="浓度点数 可接受阈值"
    )


# Default settings instance
default_qc_settings = QCSettings()
