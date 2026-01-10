#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tab 1: Tm Quality Control (V2 with Individual Flags)
======================================================
基础分析(Tab 1)的质量控制 - 重写版本

评估单个毛细管Tm测定的质量,支持:
- Two-State Boltzmann (TSB)
- Area Under Curve (AUC)
- First Derivative (FD)

**新规则**:
1. 每个QC指标独立评分: ✅绿标, ⚠️黄标, ❌红标
2. Overall评估:
   - 任何红标 → Overall红标 (一票否决)
   - 无红标,黄标≥绿标 → Overall黄标
   - 其他情况 → Overall绿标
3. 悬停显示所有细项,包括黄标内容
"""

import numpy as np
from typing import Dict, Any, Literal, List, Tuple
from pydantic import BaseModel

from .base import QualityMetrics, QualityController
from .config import default_qc_settings, QCSettings
from ..models import TmResult


class TmQualityController(QualityController):
    """Tab 1: Tm质量控制器 (V2)"""

    def __init__(self, settings: QCSettings = None):
        """
        初始化

        Args:
            settings: QC设置对象,默认使用default_qc_settings
        """
        self.settings = settings or default_qc_settings

    def evaluate(self, tm_result) -> QualityMetrics:
        """
        评估Tm结果质量

        Args:
            tm_result: Tm分析结果 (TmResult对象或字典)

        Returns:
            QualityMetrics对象
        """
        # 计算所有QC指标
        metrics = self.get_metrics(tm_result)

        # 获取method (支持dict和对象)
        if isinstance(tm_result, dict):
            method = tm_result.get('method')
        else:
            method = tm_result.method.value

        # 计算每个指标的flag
        individual_flags = self._evaluate_individual_flags(metrics, method)

        # 应用overall逻辑
        overall_flag = self._compute_overall_flag(individual_flags)

        # 计算质量分数
        score = self._calculate_score(metrics, method)

        # 生成消息
        message = self._generate_message(individual_flags, overall_flag)

        # 生成tooltip (显示所有细项,包括黄标)
        tooltip = self._generate_tooltip(individual_flags, overall_flag, metrics)

        # 将individual_flags存入details
        metrics['individual_flags'] = individual_flags

        return QualityMetrics(
            passed=(overall_flag == '✅'),
            flag=overall_flag,
            score=score,
            message=message,
            details=metrics,
            tooltip=tooltip
        )

    def get_metrics(self, tm_result) -> Dict[str, Any]:
        """
        计算所有QC指标

        Args:
            tm_result: Tm分析结果 (TmResult对象或字典)

        Returns:
            指标字典
        """
        # Support both TmResult objects and dicts
        if isinstance(tm_result, dict):
            method = tm_result.get('method')
            tm = tm_result.get('Tm')
            r_squared = tm_result.get('R_squared', 0.0)
            T = tm_result.get('T', [])
            n_points = len(T) if T is not None else 0
            t_range = np.ptp(T) if T is not None and len(T) > 0 else 0.0
        else:
            method = tm_result.method.value
            tm = tm_result.Tm
            r_squared = tm_result.R_squared if not np.isnan(tm_result.R_squared) else 0.0
            n_points = len(tm_result.raw_data.T) if tm_result.raw_data else 0
            t_range = tm_result.raw_data.T.ptp() if tm_result.raw_data else 0.0

        # Universal metrics
        metrics = {
            'method': method,
            'tm': tm,
            'r_squared': r_squared if not np.isnan(r_squared) else 0.0,
            'n_points': n_points,
            't_range': t_range,
        }

        # Method-specific metrics
        if method == 'boltzmann':
            metrics.update(self._get_tsb_metrics(tm_result))
        elif method == 'auc':
            metrics.update(self._get_auc_metrics(tm_result))
        elif method == 'derivative':
            metrics.update(self._get_fd_metrics(tm_result))

        return metrics

    def _get_tsb_metrics(self, tm_result) -> Dict[str, Any]:
        """获取TSB特定指标"""
        if isinstance(tm_result, dict):
            metrics = {
                'state_snr': tm_result.get('state_snr', float('nan')),
                'delta_aic': tm_result.get('delta_aic', 0.0),
                'log_delta_aic': tm_result.get('log_delta_aic', 0.0),
                'delta_bic': tm_result.get('delta_bic', 0.0),
                'log_delta_bic': tm_result.get('log_delta_bic', 0.0),
                'tm_error': tm_result.get('Tm_error', float('inf')),
            }
        else:
            metrics = {
                'state_snr': tm_result.state_snr if hasattr(tm_result, 'state_snr') and tm_result.state_snr is not None else float('nan'),
                'delta_aic': tm_result.delta_aic if hasattr(tm_result, 'delta_aic') and tm_result.delta_aic is not None else 0.0,
                'log_delta_aic': tm_result.log_delta_aic if hasattr(tm_result, 'log_delta_aic') and tm_result.log_delta_aic is not None else 0.0,
                'delta_bic': tm_result.delta_bic if hasattr(tm_result, 'delta_bic') and tm_result.delta_bic is not None else 0.0,
                'log_delta_bic': tm_result.log_delta_bic if hasattr(tm_result, 'log_delta_bic') and tm_result.log_delta_bic is not None else 0.0,
                'tm_error': tm_result.tm_error if tm_result.tm_error is not None else float('inf'),
            }
        return metrics

    def _get_auc_metrics(self, tm_result) -> Dict[str, Any]:
        """获取AUC特定指标"""
        if isinstance(tm_result, dict):
            metrics = {
                'dynamic_range': tm_result.get('dynamic_range_pct'),
            }
        else:
            metrics = {
                'dynamic_range': tm_result.dynamic_range if hasattr(tm_result, 'dynamic_range') else None,
            }
        return metrics

    def _get_fd_metrics(self, tm_result) -> Dict[str, Any]:
        """获取FD特定指标"""
        if isinstance(tm_result, dict):
            metrics = {
                'peak_snr': tm_result.get('peak_snr', 0.0),
                'peak_width': tm_result.get('peak_width'),
            }
        else:
            metrics = {
                'peak_snr': tm_result.snr if tm_result.snr is not None else 0.0,
                'peak_width': tm_result.peak_width if hasattr(tm_result, 'peak_width') and tm_result.peak_width is not None else None,
            }
        return metrics

    def _evaluate_individual_flags(
        self,
        metrics: Dict[str, Any],
        method: str
    ) -> Dict[str, Literal['✅', '⚠️', '❌']]:
        """
        评估每个QC指标的flag

        Args:
            metrics: QC指标字典
            method: 分析方法

        Returns:
            指标名称 → flag的字典
        """
        flags = {}

        # Critical failures (一票否决)
        if metrics['n_points'] < self.settings.min_data_points:
            flags['data_points'] = '❌'
        else:
            flags['data_points'] = '✅'

        if np.isnan(metrics['tm']):
            flags['tm_found'] = '❌'
        else:
            flags['tm_found'] = '✅'

        # Method-specific flags
        if method == 'boltzmann':
            flags.update(self._evaluate_tsb_flags(metrics))
        elif method == 'auc':
            flags.update(self._evaluate_auc_flags(metrics))
        elif method == 'derivative':
            flags.update(self._evaluate_fd_flags(metrics))

        return flags

    def _evaluate_tsb_flags(self, metrics: Dict[str, Any]) -> Dict[str, Literal['✅', '⚠️', '❌']]:
        """TSB方法的各项flag"""
        flags = {}

        # R²
        r2 = metrics['r_squared']
        if r2 >= self.settings.tm_r2_good:
            flags['r_squared'] = '✅'
        elif r2 >= self.settings.tm_r2_marginal:
            flags['r_squared'] = '⚠️'
        else:
            flags['r_squared'] = '❌'

        # State SNR: <3红, 3-10黄, ≥10绿
        state_snr = metrics.get('state_snr', float('nan'))
        if not np.isnan(state_snr):
            if state_snr >= self.settings.tm_state_snr_excellent:
                flags['state_snr'] = '✅'
            elif state_snr >= self.settings.tm_state_snr_marginal:
                flags['state_snr'] = '⚠️'
            else:
                flags['state_snr'] = '❌'
        else:
            flags['state_snr'] = '⚠️'  # 无法计算视为警告

        # ΔAIC (log scale)
        log_aic = metrics.get('log_delta_aic', 0.0)
        if log_aic >= self.settings.tm_delta_aic_preferred:
            flags['delta_aic'] = '✅'
        elif log_aic >= self.settings.tm_delta_aic_marginal:
            flags['delta_aic'] = '⚠️'
        else:
            flags['delta_aic'] = '❌'

        # ΔBIC (log scale)
        log_bic = metrics.get('log_delta_bic', 0.0)
        if log_bic >= self.settings.tm_delta_bic_preferred:
            flags['delta_bic'] = '✅'
        elif log_bic >= self.settings.tm_delta_bic_marginal:
            flags['delta_bic'] = '⚠️'
        else:
            flags['delta_bic'] = '❌'

        # Tm误差: <0.3绿, 0.3-1.0黄, >1.0红
        tm_error = metrics.get('tm_error', float('inf'))
        if tm_error < self.settings.tm_error_excellent:
            flags['tm_error'] = '✅'
        elif tm_error < self.settings.tm_error_marginal:
            flags['tm_error'] = '⚠️'
        else:
            flags['tm_error'] = '❌'

        return flags

    def _evaluate_auc_flags(self, metrics: Dict[str, Any]) -> Dict[str, Literal['✅', '⚠️', '❌']]:
        """AUC方法的各项flag"""
        flags = {}

        # R²
        r2 = metrics['r_squared']
        if r2 >= self.settings.tm_r2_good:
            flags['r_squared'] = '✅'
        elif r2 >= self.settings.tm_r2_marginal:
            flags['r_squared'] = '⚠️'
        else:
            flags['r_squared'] = '❌'

        # Dynamic range: <30%红, 30-60%黄, ≥60%绿
        dynamic_range = metrics.get('dynamic_range')
        if dynamic_range is not None:
            if dynamic_range >= self.settings.auc_dynamic_range_excellent:
                flags['dynamic_range'] = '✅'
            elif dynamic_range > self.settings.auc_dynamic_range_marginal:
                flags['dynamic_range'] = '⚠️'
            else:
                flags['dynamic_range'] = '❌'
        else:
            flags['dynamic_range'] = '⚠️'

        return flags

    def _evaluate_fd_flags(self, metrics: Dict[str, Any]) -> Dict[str, Literal['✅', '⚠️', '❌']]:
        """FD方法的各项flag"""
        flags = {}

        # Peak SNR: <3红, 3-10黄, ≥10绿
        peak_snr = metrics.get('peak_snr', 0.0)
        if peak_snr >= self.settings.fd_peak_snr_excellent:
            flags['peak_snr'] = '✅'
        elif peak_snr >= self.settings.fd_peak_snr_marginal:
            flags['peak_snr'] = '⚠️'
        else:
            flags['peak_snr'] = '❌'

        return flags

    def _compute_overall_flag(
        self,
        individual_flags: Dict[str, Literal['✅', '⚠️', '❌']]
    ) -> Literal['✅', '⚠️', '❌']:
        """
        计算overall flag

        规则:
        1. 任何红标 → Overall红标 (一票否决)
        2. 无红标,黄标≥绿标 → Overall黄标
        3. 其他情况 → Overall绿标

        Args:
            individual_flags: 各指标的flag字典

        Returns:
            Overall flag
        """
        flags_list = list(individual_flags.values())

        # Count flags
        n_red = flags_list.count('❌')
        n_yellow = flags_list.count('⚠️')
        n_green = flags_list.count('✅')

        # Rule 1: Any red → Overall red
        if n_red > 0:
            return '❌'

        # Rule 2: No red, yellow ≥ green → Overall yellow
        if n_yellow >= n_green:
            return '⚠️'

        # Rule 3: Otherwise → Overall green
        return '✅'

    def _calculate_score(self, metrics: Dict[str, Any], method: str) -> float:
        """
        计算质量分数 (0-100)

        Args:
            metrics: QC指标字典
            method: 分析方法

        Returns:
            分数 (0-100)
        """
        score = 0.0

        # Check critical failures
        if metrics['n_points'] < self.settings.min_data_points:
            return 0.0

        if np.isnan(metrics['tm']):
            return 0.0

        # Universal checks (20 points)
        if metrics['n_points'] >= 50:
            score += 10
        elif metrics['n_points'] >= self.settings.min_data_points:
            score += 5

        if metrics['t_range'] >= 40:
            score += 10
        elif metrics['t_range'] >= self.settings.min_temperature_range:
            score += 5

        # Method-specific checks (80 points)
        if method == 'boltzmann':
            score += self._score_tsb(metrics)
        elif method == 'auc':
            score += self._score_auc(metrics)
        elif method == 'derivative':
            score += self._score_fd(metrics)

        return min(100.0, score)

    def _score_tsb(self, metrics: Dict[str, Any]) -> float:
        """TSB方法评分 (0-80)"""
        score = 0.0
        r2 = metrics['r_squared']
        state_snr = metrics.get('state_snr', float('nan'))
        log_aic = metrics.get('log_delta_aic', 0.0)
        log_bic = metrics.get('log_delta_bic', 0.0)
        tm_error = metrics.get('tm_error', float('inf'))

        # R² scoring (30 points)
        if r2 >= self.settings.tm_r2_excellent:
            score += 30
        elif r2 >= self.settings.tm_r2_good:
            score += 22
        elif r2 >= self.settings.tm_r2_marginal:
            score += 15
        else:
            score += 5

        # State SNR scoring (20 points)
        if not np.isnan(state_snr):
            if state_snr >= self.settings.tm_state_snr_excellent:
                score += 20
            elif state_snr >= self.settings.tm_state_snr_marginal:
                score += 10
            else:
                score += 3

        # ΔAIC scoring (10 points)
        if log_aic >= self.settings.tm_delta_aic_strong:
            score += 10
        elif log_aic >= self.settings.tm_delta_aic_preferred:
            score += 7
        elif log_aic >= self.settings.tm_delta_aic_marginal:
            score += 4

        # ΔBIC scoring (10 points)
        if log_bic >= self.settings.tm_delta_bic_strong:
            score += 10
        elif log_bic >= self.settings.tm_delta_bic_preferred:
            score += 7
        elif log_bic >= self.settings.tm_delta_bic_marginal:
            score += 4

        # Tm error scoring (10 points)
        if tm_error < self.settings.tm_error_excellent:
            score += 10
        elif tm_error < self.settings.tm_error_good:
            score += 7
        elif tm_error < self.settings.tm_error_marginal:
            score += 4

        return score

    def _score_auc(self, metrics: Dict[str, Any]) -> float:
        """AUC方法评分 (0-80)"""
        score = 0.0
        r2 = metrics['r_squared']
        dynamic_range = metrics.get('dynamic_range')

        # R² scoring (50 points)
        if r2 >= self.settings.tm_r2_excellent:
            score += 50
        elif r2 >= self.settings.tm_r2_good:
            score += 40
        elif r2 >= self.settings.tm_r2_marginal:
            score += 25
        else:
            score += 10

        # Dynamic range scoring (30 points)
        if dynamic_range is not None:
            if dynamic_range >= self.settings.auc_dynamic_range_excellent:
                score += 30
            elif dynamic_range > self.settings.auc_dynamic_range_marginal:
                score += 15
            else:
                score += 5

        return score

    def _score_fd(self, metrics: Dict[str, Any]) -> float:
        """FD方法评分 (0-80)"""
        score = 0.0
        peak_snr = metrics.get('peak_snr', 0.0)

        # Peak SNR scoring (80 points)
        if peak_snr >= self.settings.fd_peak_snr_excellent:
            score += 80
        elif peak_snr >= self.settings.fd_peak_snr_marginal:
            score += 40
        else:
            score += 10

        return score

    def _generate_message(
        self,
        individual_flags: Dict[str, Literal['✅', '⚠️', '❌']],
        overall_flag: Literal['✅', '⚠️', '❌']
    ) -> str:
        """
        生成质量消息

        Args:
            individual_flags: 各指标的flag字典
            overall_flag: Overall flag

        Returns:
            消息字符串
        """
        if overall_flag == '✅':
            return "High quality"

        elif overall_flag == '⚠️':
            # 列出所有黄标和红标的项目
            issues = []
            for key, flag in individual_flags.items():
                if flag in ['⚠️', '❌']:
                    issues.append(self._flag_name_to_display(key))

            return "; ".join(issues) if issues else "Marginal quality"

        else:  # ❌
            # 列出所有红标的项目
            issues = []
            for key, flag in individual_flags.items():
                if flag == '❌':
                    issues.append(self._flag_name_to_display(key))

            return "; ".join(issues) if issues else "Analysis failed"

    def _generate_tooltip(
        self,
        individual_flags: Dict[str, Literal['✅', '⚠️', '❌']],
        overall_flag: Literal['✅', '⚠️', '❌'],
        metrics: Dict[str, Any]
    ) -> str | None:
        """
        生成悬停提示文本 (显示所有细项,包括黄标)

        Args:
            individual_flags: 各指标的flag字典
            overall_flag: Overall flag
            metrics: QC指标字典

        Returns:
            提示文本或None
        """
        lines = []

        for key, flag in individual_flags.items():
            display_name = self._flag_name_to_display(key)
            value_str = self._format_metric_value(key, metrics)

            lines.append(f"{flag} {display_name}: {value_str}")

        return "\n".join(lines) if lines else None

    def _flag_name_to_display(self, key: str) -> str:
        """将flag键名转换为显示名称"""
        name_map = {
            'data_points': 'Data Points',
            'tm_found': 'Tm Found',
            'r_squared': 'R²',
            'state_snr': 'State SNR',
            'delta_aic': 'ΔAIC',
            'delta_bic': 'ΔBIC',
            'tm_error': 'Tm Error',
            'dynamic_range': 'Dynamic Range',
            'peak_snr': 'Peak SNR',
        }
        return name_map.get(key, key)

    def _format_metric_value(self, key: str, metrics: Dict[str, Any]) -> str:
        """格式化指标值用于显示"""
        if key == 'data_points':
            return f"{metrics['n_points']}"
        elif key == 'tm_found':
            return "Yes" if not np.isnan(metrics['tm']) else "No"
        elif key == 'r_squared':
            return f"{metrics['r_squared']:.3f}"
        elif key == 'state_snr':
            snr = metrics.get('state_snr', float('nan'))
            return f"{snr:.1f}" if not np.isnan(snr) else "N/A"
        elif key == 'delta_aic':
            return f"{metrics.get('log_delta_aic', 0.0):.2f}"
        elif key == 'delta_bic':
            return f"{metrics.get('log_delta_bic', 0.0):.2f}"
        elif key == 'tm_error':
            err = metrics.get('tm_error', float('inf'))
            return f"±{err:.2f}°C" if err != float('inf') else "N/A"
        elif key == 'dynamic_range':
            dr = metrics.get('dynamic_range')
            return f"{dr:.0f}%" if dr is not None else "N/A"
        elif key == 'peak_snr':
            return f"{metrics.get('peak_snr', 0.0):.1f}"
        else:
            return "N/A"
