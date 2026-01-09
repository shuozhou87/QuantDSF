#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tab 2: Thermodynamic Quality Control
======================================
热力学参数推算的质量控制

评估Van't Hoff回归分析质量,支持:
- Van't Hoff regression quality (R², n_points, ΔT)
- Parameter uncertainty (ΔH, ΔS relative errors)
- KD prediction reliability (extrapolation factors)
- Physical plausibility checks
"""

import numpy as np
from typing import Dict, Any, Literal
from pydantic import BaseModel

from .base import QualityMetrics, QualityController
from .config import default_qc_settings, QCSettings


class ThermodynamicQualityController(QualityController):
    """Tab 2: 热力学分析质量控制器"""

    def __init__(self, settings: QCSettings = None):
        """
        初始化

        Args:
            settings: QC设置对象,默认使用default_qc_settings
        """
        self.settings = settings or default_qc_settings

    def evaluate(self, thermo_result: Dict[str, Any]) -> QualityMetrics:
        """
        评估热力学分析质量

        Args:
            thermo_result: 热力学分析结果字典

        Returns:
            QualityMetrics对象
        """
        # 计算所有QC指标
        metrics = self.get_metrics(thermo_result)

        # 计算质量分数
        score = self._calculate_score(metrics)

        # 分配质量标志
        flag = self._assign_flag_from_metrics(metrics)

        # 生成消息
        message = self._generate_message(metrics, flag)

        # 生成tooltip
        tooltip = self._generate_tooltip(flag, metrics)

        return QualityMetrics(
            passed=(flag == '✅'),
            flag=flag,
            score=score,
            message=message,
            details=metrics,
            tooltip=tooltip
        )

    def get_metrics(self, thermo_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算所有QC指标

        Args:
            thermo_result: 热力学分析结果字典
                必需字段:
                - vh_r2: Van't Hoff回归R²
                - vh_n_points: 回归点数
                - delta_T: 温度范围
                - dH: 焓变 (J/mol)
                - dS: 熵变 (J/mol/K)
                - dH_err: 焓变标准误差
                - dS_err: 熵变标准误差
                - Kd_298K: 298K时的解离常数 (M)
                - Kd_310K: 310K时的解离常数 (M)
                - T_min: 最小温度 (K)
                - T_max: 最大温度 (K)

        Returns:
            指标字典
        """
        # Basic regression metrics
        vh_r2 = thermo_result.get('vh_r2', 0.0)
        vh_n_points = thermo_result.get('vh_n_points', 0)
        delta_T = thermo_result.get('delta_T', 0.0)

        # Thermodynamic parameters
        dH = thermo_result.get('dH', 0.0)
        dS = thermo_result.get('dS', 0.0)
        dH_err = thermo_result.get('dH_err', 0.0)
        dS_err = thermo_result.get('dS_err', 0.0)

        # Calculate relative errors
        dH_rel_err = abs(dH_err / dH) if dH != 0 else float('inf')
        dS_rel_err = abs(dS_err / dS) if dS != 0 else float('inf')

        # KD predictions
        Kd_298K = thermo_result.get('Kd_298K')
        Kd_310K = thermo_result.get('Kd_310K')

        # Temperature range for extrapolation assessment
        T_min = thermo_result.get('T_min', 298.15)
        T_max = thermo_result.get('T_max', 363.15)

        # Calculate extrapolation factors
        extrap_298 = self._calculate_extrapolation_factor(298.15, T_min, T_max)
        extrap_310 = self._calculate_extrapolation_factor(310.15, T_min, T_max)

        # Assess KD reliability
        reliability_298 = self._assess_kd_reliability(extrap_298, vh_r2, dH_rel_err)
        reliability_310 = self._assess_kd_reliability(extrap_310, vh_r2, dH_rel_err)

        # Physical plausibility checks
        dH_plausible = self._check_dH_plausibility(dH)
        dS_plausible = self._check_dS_plausibility(dS)

        metrics = {
            # Regression quality
            'vh_r2': vh_r2,
            'vh_n_points': vh_n_points,
            'delta_T': delta_T,

            # Parameter uncertainty
            'dH': dH,
            'dS': dS,
            'dH_rel_err': dH_rel_err,
            'dS_rel_err': dS_rel_err,

            # KD predictions
            'Kd_298K': Kd_298K,
            'Kd_310K': Kd_310K,
            'extrap_298': extrap_298,
            'extrap_310': extrap_310,
            'reliability_298': reliability_298,
            'reliability_310': reliability_310,

            # Physical plausibility
            'dH_plausible': dH_plausible,
            'dS_plausible': dS_plausible,
        }

        return metrics

    def _calculate_extrapolation_factor(
        self,
        T_target: float,
        T_min: float,
        T_max: float
    ) -> float:
        """
        计算外推因子

        Args:
            T_target: 目标温度 (K)
            T_min: 最小实验温度 (K)
            T_max: 最大实验温度 (K)

        Returns:
            外推因子 (0 = 内插, >0 = 外推)
        """
        if T_min <= T_target <= T_max:
            return 0.0  # Interpolation
        elif T_target < T_min:
            return (T_min - T_target) / (T_max - T_min)
        else:  # T_target > T_max
            return (T_target - T_max) / (T_max - T_min)

    def _assess_kd_reliability(
        self,
        extrap_factor: float,
        r2: float,
        rel_err: float
    ) -> Literal['HIGH', 'MEDIUM', 'LOW', 'VERY LOW']:
        """
        评估KD预测可靠性

        Args:
            extrap_factor: 外推因子
            r2: Van't Hoff回归R²
            rel_err: ΔH相对误差

        Returns:
            可靠性等级
        """
        # Interpolation (within experimental range)
        if extrap_factor == 0.0:
            if r2 >= self.settings.thermo_r2_excellent and rel_err < 0.10:
                return 'HIGH'
            elif r2 >= self.settings.thermo_r2_good and rel_err < 0.20:
                return 'MEDIUM'
            elif r2 >= self.settings.thermo_r2_marginal:
                return 'LOW'
            else:
                return 'VERY LOW'

        # Minor extrapolation (< 0.2 × range)
        elif extrap_factor < 0.2:
            if r2 >= self.settings.thermo_r2_excellent and rel_err < 0.10:
                return 'HIGH'
            elif r2 >= self.settings.thermo_r2_good and rel_err < 0.15:
                return 'MEDIUM'
            else:
                return 'LOW'

        # Moderate extrapolation (0.2-0.5 × range)
        elif extrap_factor < 0.5:
            if r2 >= self.settings.thermo_r2_excellent and rel_err < 0.10:
                return 'MEDIUM'
            elif r2 >= self.settings.thermo_r2_good:
                return 'LOW'
            else:
                return 'VERY LOW'

        # Major extrapolation (> 0.5 × range)
        else:
            if r2 >= self.settings.thermo_r2_excellent and rel_err < 0.10:
                return 'LOW'
            else:
                return 'VERY LOW'

    def _check_dH_plausibility(self, dH: float) -> bool:
        """
        检查ΔH物理合理性

        典型蛋白质解折叠: -800 to -50 kJ/mol

        Args:
            dH: 焓变 (J/mol)

        Returns:
            是否合理
        """
        dH_kJ = dH / 1000.0
        return -800 <= dH_kJ <= -50

    def _check_dS_plausibility(self, dS: float) -> bool:
        """
        检查ΔS物理合理性

        典型蛋白质解折叠: -2500 to 0 J/mol/K

        Args:
            dS: 熵变 (J/mol/K)

        Returns:
            是否合理
        """
        return -2500 <= dS <= 0

    def _calculate_score(self, metrics: Dict[str, Any]) -> float:
        """
        计算质量分数 (0-100)

        Args:
            metrics: QC指标字典

        Returns:
            分数 (0-100)
        """
        score = 0.0

        # Regression quality (40 points)
        r2 = metrics['vh_r2']
        if r2 >= self.settings.thermo_r2_excellent:
            score += 20
        elif r2 >= self.settings.thermo_r2_good:
            score += 15
        elif r2 >= self.settings.thermo_r2_marginal:
            score += 10
        else:
            score += 5

        n_points = metrics['vh_n_points']
        if n_points >= self.settings.thermo_min_points_excellent:
            score += 10
        elif n_points >= self.settings.thermo_min_points_good:
            score += 7
        else:
            score += 4

        delta_T = metrics['delta_T']
        if delta_T >= self.settings.thermo_min_delta_T_excellent:
            score += 10
        elif delta_T >= self.settings.thermo_min_delta_T_good:
            score += 7
        else:
            score += 4

        # Parameter uncertainty (30 points)
        dH_rel_err = metrics['dH_rel_err']
        if dH_rel_err < 0.05:
            score += 15
        elif dH_rel_err < 0.10:
            score += 12
        elif dH_rel_err < 0.20:
            score += 8
        else:
            score += 4

        dS_rel_err = metrics['dS_rel_err']
        if dS_rel_err < 0.05:
            score += 15
        elif dS_rel_err < 0.10:
            score += 12
        elif dS_rel_err < 0.20:
            score += 8
        else:
            score += 4

        # Physical plausibility (15 points)
        if metrics['dH_plausible']:
            score += 7.5

        if metrics['dS_plausible']:
            score += 7.5

        # KD reliability (15 points)
        reliability_map = {'HIGH': 15, 'MEDIUM': 10, 'LOW': 5, 'VERY LOW': 0}
        # Use better of the two predictions
        best_reliability = max(
            reliability_map[metrics['reliability_298']],
            reliability_map[metrics['reliability_310']]
        )
        score += best_reliability

        return min(100.0, score)

    def _assign_flag_from_metrics(
        self,
        metrics: Dict[str, Any]
    ) -> Literal['✅', '⚠️', '❌']:
        """
        根据指标分配质量标志

        Args:
            metrics: QC指标字典

        Returns:
            质量标志
        """
        r2 = metrics['vh_r2']
        n_points = metrics['vh_n_points']
        dH_rel_err = metrics['dH_rel_err']
        dH_plausible = metrics['dH_plausible']
        dS_plausible = metrics['dS_plausible']

        # Critical failures
        if r2 < self.settings.thermo_r2_marginal:
            return '❌'

        if n_points < self.settings.thermo_min_points_good:
            return '❌'

        if not dH_plausible or not dS_plausible:
            return '❌'

        # Warning conditions
        if r2 < self.settings.thermo_r2_good:
            return '⚠️'

        if dH_rel_err > 0.20:
            return '⚠️'

        if n_points < self.settings.thermo_min_points_excellent:
            return '⚠️'

        # Pass
        return '✅'

    def _generate_message(
        self,
        metrics: Dict[str, Any],
        flag: Literal['✅', '⚠️', '❌']
    ) -> str:
        """
        生成质量消息

        Args:
            metrics: QC指标字典
            flag: 质量标志

        Returns:
            消息字符串
        """
        if flag == '✅':
            return "High reliability"

        elif flag == '⚠️':
            issues = []

            r2 = metrics['vh_r2']
            if r2 < self.settings.thermo_r2_good:
                issues.append(f"Low R²: {r2:.3f}")

            dH_rel_err = metrics['dH_rel_err']
            if dH_rel_err > 0.20:
                issues.append(f"High ΔH error: {dH_rel_err:.1%}")

            n_points = metrics['vh_n_points']
            if n_points < self.settings.thermo_min_points_excellent:
                issues.append(f"Few points: {n_points}")

            return "; ".join(issues) if issues else "Marginal reliability"

        else:  # ❌
            r2 = metrics['vh_r2']
            if r2 < self.settings.thermo_r2_marginal:
                return f"Poor Van't Hoff fit (R²={r2:.3f})"

            n_points = metrics['vh_n_points']
            if n_points < self.settings.thermo_min_points_good:
                return f"Insufficient data points ({n_points})"

            if not metrics['dH_plausible']:
                dH_kJ = metrics['dH'] / 1000.0
                return f"Implausible ΔH ({dH_kJ:.0f} kJ/mol)"

            if not metrics['dS_plausible']:
                dS = metrics['dS']
                return f"Implausible ΔS ({dS:.0f} J/mol/K)"

            return "Thermodynamic analysis unreliable"

    def _generate_tooltip(
        self,
        flag: Literal['✅', '⚠️', '❌'],
        metrics: Dict[str, Any]
    ) -> str | None:
        """
        生成悬停提示文本

        Args:
            flag: 质量标志
            metrics: QC指标字典

        Returns:
            提示文本或None
        """
        if flag == '✅':
            # Pass: Show key metrics
            r2 = metrics['vh_r2']
            n_points = metrics['vh_n_points']
            reliability_298 = metrics['reliability_298']
            reliability_310 = metrics['reliability_310']

            return (f"R²={r2:.3f}, n={n_points}, "
                   f"KD(298K)={reliability_298}, KD(310K)={reliability_310}")

        elif flag == '⚠️':
            # Warning: Show specific issues with thresholds
            issues = []

            r2 = metrics['vh_r2']
            if r2 < self.settings.thermo_r2_good:
                issues.append(f"R²: {r2:.3f} (threshold: {self.settings.thermo_r2_good})")

            dH_rel_err = metrics['dH_rel_err']
            if dH_rel_err > 0.20:
                issues.append(f"ΔH error: {dH_rel_err:.1%} (threshold: 20%)")

            n_points = metrics['vh_n_points']
            if n_points < self.settings.thermo_min_points_excellent:
                issues.append(f"Points: {n_points} (recommended: {self.settings.thermo_min_points_excellent})")

            return "; ".join(issues) if issues else "Marginal reliability"

        else:  # ❌
            # Fail: Show failure reason
            return self._generate_message(metrics, flag)
