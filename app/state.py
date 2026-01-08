#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application State Management
=============================
集中式状态管理

设计原则:
- 所有状态集中管理，避免分散
- 状态更新有明确的入口
- 便于调试和持久化
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class AppState:
    """
    应用状态
    
    集中管理所有 UI 和数据状态
    注意：这是简化版本，用于骨架运行测试
    """
    
    # =========== 数据状态 ===========
    uploaded_files: List[str] = field(default_factory=list)
    capillaries: List[Any] = field(default_factory=list)
    
    # =========== 分析状态 ===========
    tm_results: List[Any] = field(default_factory=list)
    ec50_data: List[Any] = field(default_factory=list)
    vanthoff_result: Optional[Any] = None
    
    # =========== UI 状态 ===========
    active_tab: str = "basic"
    selected_capillary_indices: List[int] = field(default_factory=list)
    selected_ec50_indices: List[int] = field(default_factory=list)
    
    # =========== 缓存 ===========
    _cache: Dict[str, Any] = field(default_factory=dict)
    _last_analysis_time: Optional[datetime] = None
    
    def reset(self) -> None:
        """重置所有状态"""
        self.uploaded_files = []
        self.capillaries = []
        self.tm_results = []
        self.ec50_data = []
        self.vanthoff_result = None
        self.selected_capillary_indices = []
        self.selected_ec50_indices = []
        self._cache = {}
        self._last_analysis_time = None
    
    @property
    def has_data(self) -> bool:
        """是否有数据"""
        return len(self.capillaries) > 0
    
    @property
    def has_results(self) -> bool:
        """是否有结果"""
        return len(self.tm_results) > 0

