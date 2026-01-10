#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Quality Control Classes
==============================
QC模块的基础类和接口
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal, Optional, List


class QualityMetrics(BaseModel):
    """质量评估结果"""

    passed: bool = Field(
        ...,
        description="是否通过质量检查"
    )

    flag: Literal['✅', '⚠️', '❌'] = Field(
        ...,
        description="质量标志: ✅ 通过, ⚠️ 警告, ❌ 失败"
    )

    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="质量分数 (0-100)"
    )

    message: str = Field(
        ...,
        description="质量评估消息"
    )

    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="详细的QC指标"
    )

    tooltip: Optional[str] = Field(
        None,
        description="悬停提示文本"
    )

    reason_codes: List[str] = Field(
        default_factory=list,
        description="标准化的QC原因代码列表 (machine-readable)"
    )


class QualityController(ABC):
    """抽象质量控制器基类"""

    @abstractmethod
    def evaluate(self, data: Any) -> QualityMetrics:
        """
        评估数据质量

        Args:
            data: 待评估的数据对象

        Returns:
            QualityMetrics对象
        """
        pass

    @abstractmethod
    def get_metrics(self, data: Any) -> Dict[str, Any]:
        """
        计算所有QC指标

        Args:
            data: 待评估的数据对象

        Returns:
            指标字典
        """
        pass

    def _assign_flag(self, score: float) -> Literal['✅', '⚠️', '❌']:
        """
        根据分数分配质量标志

        Args:
            score: 质量分数 (0-100)

        Returns:
            质量标志
        """
        if score >= 80:
            return '✅'
        elif score >= 50:
            return '⚠️'
        else:
            return '❌'

    def _generate_tooltip(
        self,
        flag: Literal['✅', '⚠️', '❌'],
        metrics: Dict[str, Any]
    ) -> Optional[str]:
        """
        生成悬停提示文本

        Args:
            flag: 质量标志
            metrics: QC指标字典

        Returns:
            提示文本或None
        """
        if flag == '✅':
            # 通过: 简短摘要或不显示
            return None

        elif flag == '⚠️':
            # 警告: 显示具体问题和阈值
            issues = []
            for key, value in metrics.items():
                if key.endswith('_threshold') or key.endswith('_passed'):
                    continue
                # 添加具体的警告信息
                if isinstance(value, (int, float)) and value < metrics.get(f'{key}_threshold', float('inf')):
                    threshold = metrics.get(f'{key}_threshold', 'N/A')
                    issues.append(f"{key}: {value:.3f} (threshold: {threshold})")

            return '; '.join(issues) if issues else "Marginal quality"

        else:  # ❌
            # 失败: 显示失败原因
            return metrics.get('failure_reason', 'Analysis failed or quality too low')
