#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tab 3: Dose-Response Quality Control
=====================================
剂量-响应曲线拟合的质量控制

评估4PL (Four-Parameter Logistic) 拟合质量,支持:
- Fit quality (R²)
- Dynamic range
- Hill slope
- Concentration coverage
- Parameter uncertainty
"""

import numpy as np
from typing import Dict, Any, Literal
from pydantic import BaseModel

from .base import QualityMetrics, QualityController
from .config import default_qc_settings, QCSettings


class DoseResponseQualityController(QualityController):
    """Tab 3: 剂量-响应质量控制器"""

    def __init__(self, settings: QCSettings = None):
        """
        初始化

        Args:
            settings: QC设置对象,默认使用default_qc_settings
        """
        self.settings = settings or default_qc_settings

    def evaluate(self, dr_result: Dict[str, Any]) -> QualityMetrics:
        """
        评估剂量-响应拟合质量

        Args:
            dr_result: 剂量-响应分析结果字典

        Returns:
            QualityMetrics对象
        """
        # 计算所有QC指标
        metrics = self.get_metrics(dr_result)

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

    def get_metrics(self, dr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算所有QC指标

        Args:
            dr_result: 剂量-响应分析结果字典
                必需字段:
                - r_squared: 拟合R²
                - n_points: 数据点数
                - bottom: 底部平台值
                - top: 顶部平台值
                - hill_slope: Hill斜率
                - EC50: 半数有效浓度 (M)
                - EC50_err: EC50标准误差
                - concentrations: 浓度数组 (M)

        Returns:
            指标字典
        """
        # Basic fit metrics
        r_squared = dr_result.get('r_squared', 0.0)
        n_points = dr_result.get('n_points', 0)

        # 4PL parameters
        bottom = dr_result.get('bottom', 0.0)
        top = dr_result.get('top', 100.0)
        hill_slope = dr_result.get('hill_slope', 1.0)
        EC50 = dr_result.get('EC50')
        EC50_err = dr_result.get('EC50_err')

        # Calculate dynamic range (理论范围: top vs bottom, in °C)
        dynamic_range = abs(top - bottom)  # Theoretical Tm shift range in °C

        # Calculate data coverage (实际数据覆盖理论动态范围的百分比)
        # Data coverage = (实验Tm_max - 实验Tm_min) / (Top - Bottom) × 100%
        responses = dr_result.get('responses', [])
        if responses and len(responses) > 0 and dynamic_range > 0:
            response_array = np.array(responses)
            data_min = response_array.min()
            data_max = response_array.max()
            experimental_range = abs(data_max - data_min)
            data_coverage_pct = (experimental_range / dynamic_range) * 100.0
        else:
            data_coverage_pct = 0.0

        # Store dynamic_range_pct as data_coverage_pct (they measure the same thing)
        # dynamic_range_pct will be used for QC thresholds
        dynamic_range_pct = data_coverage_pct

        # Calculate EC50 relative error
        EC50_rel_err = abs(EC50_err / EC50) if EC50 is not None and EC50 > 0 and EC50_err is not None else float('inf')

        # Concentration coverage
        concentrations = dr_result.get('concentrations', [])
        if concentrations and len(concentrations) > 0:
            conc_array = np.array(concentrations)
            conc_range = np.log10(conc_array.max() / conc_array.min()) if conc_array.min() > 0 else 0.0
        else:
            conc_range = 0.0

        # Check if EC50 is within concentration range
        EC50_in_range = False
        if EC50 is not None and concentrations and len(concentrations) > 0:
            conc_array = np.array(concentrations)
            EC50_in_range = (conc_array.min() <= EC50 <= conc_array.max())

        # Hill slope plausibility (typical: 0.5-4.0)
        hill_plausible = 0.5 <= abs(hill_slope) <= 4.0

        metrics = {
            # Fit quality
            'r_squared': r_squared,
            'n_points': n_points,

            # 4PL parameters
            'bottom': bottom,
            'top': top,
            'dynamic_range': dynamic_range,
            'dynamic_range_pct': dynamic_range_pct,
            'data_coverage_pct': data_coverage_pct,  # 实际数据覆盖范围
            'hill_slope': hill_slope,
            'hill_plausible': hill_plausible,

            # EC50 metrics
            'EC50': EC50,
            'EC50_err': EC50_err,
            'EC50_rel_err': EC50_rel_err,
            'EC50_in_range': EC50_in_range,

            # Concentration coverage
            'conc_range': conc_range,
            'n_concentrations': len(set(concentrations)) if concentrations else 0,
        }

        return metrics

    def _calculate_score(self, metrics: Dict[str, Any]) -> float:
        """
        计算质量分数 (0-100)

        Args:
            metrics: QC指标字典

        Returns:
            分数 (0-100)
        """
        score = 0.0

        # R² scoring (35 points)
        r2 = metrics['r_squared']
        if r2 >= self.settings.dr_r2_excellent:
            score += 35
        elif r2 >= self.settings.dr_r2_good:
            score += 28
        elif r2 >= self.settings.dr_r2_marginal:
            score += 20
        else:
            score += 10

        # Dynamic range scoring (25 points)
        dynamic_range_pct = metrics['dynamic_range_pct']
        if dynamic_range_pct >= self.settings.dr_dynamic_range_excellent:
            score += 25
        elif dynamic_range_pct >= self.settings.dr_dynamic_range_good:
            score += 18
        elif dynamic_range_pct >= self.settings.dr_dynamic_range_marginal:
            score += 12
        else:
            score += 5

        # Hill slope scoring (15 points)
        hill_slope = abs(metrics['hill_slope'])
        hill_plausible = metrics['hill_plausible']

        if hill_plausible:
            if 0.8 <= hill_slope <= 2.0:
                score += 15  # Ideal range
            else:
                score += 10  # Plausible but not ideal
        else:
            score += 5  # Implausible

        # EC50 reliability (15 points)
        EC50_in_range = metrics['EC50_in_range']
        EC50_rel_err = metrics['EC50_rel_err']

        if EC50_in_range:
            if EC50_rel_err < 0.20:
                score += 15
            elif EC50_rel_err < 0.50:
                score += 10
            else:
                score += 5
        else:
            score += 3  # Extrapolated EC50

        # Concentration coverage (10 points)
        conc_range = metrics['conc_range']
        n_conc = metrics['n_concentrations']

        if conc_range >= 3.0 and n_conc >= 6:
            score += 10
        elif conc_range >= 2.0 and n_conc >= 5:
            score += 7
        elif conc_range >= 1.5 and n_conc >= 4:
            score += 5
        else:
            score += 2

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
        r2 = metrics['r_squared']
        dynamic_range_pct = metrics['dynamic_range_pct']
        hill_plausible = metrics['hill_plausible']
        n_conc = metrics['n_concentrations']

        # Critical failures
        if r2 < self.settings.dr_r2_marginal:
            return '❌'

        if dynamic_range_pct < self.settings.dr_dynamic_range_marginal:
            return '❌'

        if not hill_plausible:
            return '❌'

        if n_conc < 4:
            return '❌'

        # Warning conditions
        if r2 < self.settings.dr_r2_good:
            return '⚠️'

        if dynamic_range_pct < self.settings.dr_dynamic_range_good:
            return '⚠️'

        if not metrics['EC50_in_range']:
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
            return "High quality fit"

        elif flag == '⚠️':
            issues = []

            r2 = metrics['r_squared']
            if r2 < self.settings.dr_r2_good:
                issues.append(f"Low R²: {r2:.3f}")

            dynamic_range_pct = metrics['dynamic_range_pct']
            if dynamic_range_pct < self.settings.dr_dynamic_range_good:
                issues.append(f"Low data coverage: {dynamic_range_pct:.1f}%")

            if not metrics['EC50_in_range']:
                issues.append("EC50 outside concentration range")

            return "; ".join(issues) if issues else "Marginal fit quality"

        else:  # ❌
            r2 = metrics['r_squared']
            if r2 < self.settings.dr_r2_marginal:
                return f"Poor fit quality (R²={r2:.3f})"

            dynamic_range_pct = metrics['dynamic_range_pct']
            if dynamic_range_pct < self.settings.dr_dynamic_range_marginal:
                return f"Insufficient data coverage ({dynamic_range_pct:.1f}%)"

            if not metrics['hill_plausible']:
                hill_slope = metrics['hill_slope']
                return f"Implausible Hill slope ({hill_slope:.2f})"

            n_conc = metrics['n_concentrations']
            if n_conc < 4:
                return f"Insufficient concentrations ({n_conc})"

            return "Dose-response fit failed"

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
            r2 = metrics['r_squared']
            dynamic_range_pct = metrics['dynamic_range_pct']
            hill_slope = metrics['hill_slope']

            return f"R²={r2:.3f}, Coverage={dynamic_range_pct:.1f}%, Hill={hill_slope:.2f}"

        elif flag == '⚠️':
            # Warning: Show specific issues with thresholds
            issues = []

            r2 = metrics['r_squared']
            if r2 < self.settings.dr_r2_good:
                issues.append(f"R²: {r2:.3f} (threshold: {self.settings.dr_r2_good})")

            dynamic_range_pct = metrics['dynamic_range_pct']
            if dynamic_range_pct < self.settings.dr_dynamic_range_good:
                issues.append(f"Coverage: {dynamic_range_pct:.1f}% (threshold: {self.settings.dr_dynamic_range_good}%)")

            if not metrics['EC50_in_range']:
                issues.append("EC50 extrapolated")

            return "; ".join(issues) if issues else "Marginal fit quality"

        else:  # ❌
            # Fail: Show failure reason
            return self._generate_message(metrics, flag)
