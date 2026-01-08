#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis Pipeline
==================
分析流程编排 - 协调各模块执行分析

使用示例:
    pipeline = AnalysisPipeline(config)
    pipeline.load_data(file_obj)
    pipeline.run_tm_analysis()
    pipeline.run_thermodynamic_analysis()
    results = pipeline.get_results()
"""

from typing import List, Optional, Any, Dict
import numpy as np

from .models import (
    CapillaryData, TmResult, AnalysisConfig, 
    VanHoffResult, EC50Data
)
from .io.parsers import parse_zip_file
from .analysis.tm import calculate_tm
from .analysis.thermodynamic import (
    build_isothermal_dataset,
    compute_isothermal_ec50,
    run_vanthoff_analysis,
)
from .analysis.thermodynamic.ec50_kd import update_ec50_data_with_kd


class AnalysisPipeline:
    """
    分析管道
    
    负责协调数据加载、Tm 分析、热力学分析等流程
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        初始化管道
        
        Args:
            config: 分析配置，若 None 则使用默认配置
        """
        self.config = config or AnalysisConfig()
        
        # 数据
        self.capillaries: List[CapillaryData] = []
        self.source_files: List[str] = []
        
        # 结果
        self.tm_results: List[TmResult] = []
        self.ec50_data: List[EC50Data] = []
        self.vanthoff_result: Optional[VanHoffResult] = None
        
        # 状态
        self._data_loaded = False
        self._tm_analyzed = False
        self._thermo_analyzed = False
    
    def load_data(self, file_obj, filename: str = "unknown") -> int:
        """
        加载数据
        
        Args:
            file_obj: 文件对象
            filename: 文件名
        
        Returns:
            加载的毛细管数量
        """
        caps = parse_zip_file(
            file_obj,
            channel=self.config.channel,
            prefer_processed=self.config.prefer_processed
        )
        
        self.capillaries.extend(caps)
        self.source_files.append(filename)
        self._data_loaded = True
        
        return len(caps)
    
    def run_tm_analysis(self) -> List[TmResult]:
        """
        运行 Tm 分析
        
        Returns:
            TmResult 列表
        """
        if not self._data_loaded:
            raise RuntimeError("请先加载数据")
        
        self.tm_results = []
        
        for cap in self.capillaries:
            result = calculate_tm(cap.raw_data, self.config)
            
            # 附加进度曲线信息（用于热力学分析）
            if hasattr(result, 'progress_curve') and result.progress_curve:
                cap._progress_curve = result.progress_curve
                cap._progress_temperature = result.progress_temperature
            
            self.tm_results.append(result)
        
        self._tm_analyzed = True
        return self.tm_results
    
    def run_thermodynamic_analysis(
        self,
        selected_capillary_indices: Optional[List[int]] = None,
        selected_ec50_indices: Optional[List[int]] = None
    ) -> VanHoffResult:
        """
        运行热力学分析
        
        Args:
            selected_capillary_indices: 选中的毛细管索引
            selected_ec50_indices: 选中的 EC50 数据点索引
        
        Returns:
            VanHoffResult
        """
        if not self._tm_analyzed:
            raise RuntimeError("请先运行 Tm 分析")
        
        # 筛选有浓度和进度曲线的毛细管
        if selected_capillary_indices is None:
            selected_caps = [
                cap for cap in self.capillaries
                if cap.has_concentration and hasattr(cap, '_progress_curve')
            ]
            selected_results = [
                res for cap, res in zip(self.capillaries, self.tm_results)
                if cap.has_concentration and hasattr(cap, '_progress_curve')
            ]
        else:
            selected_caps = [self.capillaries[i] for i in selected_capillary_indices]
            selected_results = [self.tm_results[i] for i in selected_capillary_indices]
        
        if len(selected_caps) < 4:
            raise ValueError("需要至少 4 个有效浓度点进行热力学分析")
        
        # 构建进度曲线数据
        progress_curves = []
        for cap, res in zip(selected_caps, selected_results):
            if hasattr(cap, '_progress_curve') and cap._progress_curve:
                progress_curves.append({
                    'concentration': cap.concentration,
                    'T': cap._progress_temperature,
                    'progress': [p * 100 for p in cap._progress_curve]  # 转换为百分比
                })
        
        # 构建等温数据集
        T_grid, concentrations, Y_folded = build_isothermal_dataset(
            progress_curves,
            t_step=self.config.isothermal_slice_step
        )
        
        # 计算等温 EC50
        self.ec50_data = compute_isothermal_ec50(
            T_grid, concentrations, Y_folded,
            min_dynamic_range=self.config.min_dynamic_range,
            min_r2=self.config.min_4pl_r2
        )
        
        # 更新 KD（如果有蛋白浓度）
        if self.config.protein_concentration:
            self.ec50_data = update_ec50_data_with_kd(
                self.ec50_data,
                self.config.protein_concentration
            )
        
        # 应用用户选择
        if selected_ec50_indices:
            for i, data in enumerate(self.ec50_data):
                data.is_selected = i in selected_ec50_indices
        
        # Van't Hoff 分析
        self.vanthoff_result = run_vanthoff_analysis(
            self.ec50_data,
            self.config,
            self.config.protein_concentration
        )
        
        self._thermo_analyzed = True
        return self.vanthoff_result
    
    def get_results_summary(self) -> Dict[str, Any]:
        """
        获取结果摘要
        
        Returns:
            结果摘要字典
        """
        summary = {
            'n_samples': len(self.capillaries),
            'source_files': self.source_files,
            'method': self.config.method.value,
            'channel': self.config.channel,
        }
        
        if self.tm_results:
            valid_tms = [r.tm for r in self.tm_results if not np.isnan(r.tm)]
            summary['mean_tm'] = float(np.mean(valid_tms)) if valid_tms else None
            summary['std_tm'] = float(np.std(valid_tms)) if valid_tms else None
        
        if self.vanthoff_result:
            summary['delta_h'] = self.vanthoff_result.thermodynamics.delta_h
            summary['delta_s'] = self.vanthoff_result.thermodynamics.delta_s
            summary['kd_298k'] = self.vanthoff_result.kd_298k
            summary['kd_310k'] = self.vanthoff_result.kd_310k
            summary['vanthoff_r2'] = self.vanthoff_result.r_squared
        
        return summary
    
    def reset(self) -> None:
        """重置管道状态"""
        self.capillaries = []
        self.source_files = []
        self.tm_results = []
        self.ec50_data = []
        self.vanthoff_result = None
        self._data_loaded = False
        self._tm_analyzed = False
        self._thermo_analyzed = False


