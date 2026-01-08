#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Data Parsers
=============
数据解析器模块

支持 Prometheus NT.48 和 Tycho NT.6 格式
"""
import os
import zipfile
import io
import numpy as np
from typing import List, Dict, Any, Optional, Union

from .prometheus import parse_prometheus_csv, is_prometheus_file
from .tycho import parse_tycho_nt6_csv, parse_tycho_nt6_excel, is_tycho_file
from ...utils import parse_concentration


def detect_instrument_type(file_content: Union[bytes, str], file_path: str) -> str:
    """
    检测仪器类型
    
    Args:
        file_content: 文件内容
        file_path: 文件路径
    
    Returns:
        仪器类型: 'prometheus', 'tycho_nt6', 或 'unknown'
    """
    filename = os.path.basename(file_path).lower()
    
    # 排除文档文件
    if any(filename.startswith(prefix) for prefix in ['readme', 'info', 'documentation', 'metadata']):
        return 'unknown'
    
    if is_prometheus_file(file_content, file_path):
        return 'prometheus'
    
    if is_tycho_file(file_content, file_path):
        return 'tycho_nt6'
    
    return 'unknown'


def parse_instrument_file(
    file_content: Union[str, bytes], 
    file_path: str, 
    instrument_type: Optional[str] = None,
    target_channel: Optional[str] = None
) -> Union[tuple, List[tuple]]:
    """
    根据仪器类型解析 nanoDSF 文件
    
    Args:
        file_content: 文件内容
        file_path: 文件路径
        instrument_type: 强制指定仪器类型，或 None 自动检测
        target_channel: 要提取的特定通道
    
    Returns:
        单样品文件返回元组，多样品文件返回元组列表
    """
    if instrument_type is None:
        instrument_type = detect_instrument_type(file_content, file_path)
    
    if instrument_type == 'prometheus':
        return parse_prometheus_csv(file_content, file_path)
    elif instrument_type == 'tycho_nt6':
        if file_path.lower().endswith('.xlsx'):
            return parse_tycho_nt6_excel(file_content, file_path, target_channel)
        else:
            return parse_tycho_nt6_csv(file_content, file_path)
    else:
        raise ValueError(f"不支持的仪器类型: {instrument_type}")


def parse_zip_file(
    file_obj,
    channel: str = 'ratio',
    prefer_processed: bool = False,
    debug_callback: Optional[callable] = None
) -> List[Dict[str, Any]]:
    """
    从 ZIP 文件中解析毛细管数据
    
    Args:
        file_obj: ZIP 文件对象
        channel: 数据通道
        prefer_processed: 是否优先使用处理过的数据
        debug_callback: 调试日志回调函数
    
    Returns:
        毛细管数据列表
    """
    def log_debug(message):
        if debug_callback:
            debug_callback(message)
    
    capillaries = []
    
    try:
        with zipfile.ZipFile(file_obj, 'r') as z:
            all_files = z.namelist()
            
            # 过滤相关文件
            relevant_files = _find_relevant_files(all_files, channel, prefer_processed)
            
            log_debug(f"找到 {len(relevant_files)} 个相关文件")
            
            for file_path in relevant_files:
                try:
                    raw_content = z.read(file_path)
                    
                    instrument_type = detect_instrument_type(raw_content, file_path)
                    log_debug(f"文件 {file_path}: 检测为 {instrument_type}")
                    
                    if instrument_type in ['prometheus', 'tycho_nt6']:
                        parsed_result = parse_instrument_file(
                            raw_content, file_path, instrument_type, channel
                        )
                        
                        if isinstance(parsed_result, tuple):
                            sample_data = [parsed_result]
                        else:
                            sample_data = parsed_result
                        
                        for T, F, capillary_id in sample_data:
                            if len(T) != len(F) or len(T) < 10:
                                log_debug(f"跳过 {capillary_id}: 数据不足")
                                continue
                            
                            concentration = parse_concentration(file_path)
                            
                            capillaries.append({
                                'id': capillary_id,
                                'name': capillary_id,
                                'T': np.array(T),
                                'F': np.array(F),
                                'concentration': concentration,
                                'source_file': file_path,
                                'instrument_type': instrument_type
                            })
                            
                            log_debug(f"加载毛细管 {capillary_id}: {len(T)} 个数据点")
                
                except Exception as e:
                    log_debug(f"处理文件 {file_path} 时出错: {str(e)}")
                    continue
        
        log_debug(f"成功提取 {len(capillaries)} 个毛细管")
        return capillaries
        
    except Exception as e:
        log_debug(f"读取 ZIP 文件时出错: {str(e)}")
        raise ValueError(f"读取 ZIP 文件时出错: {str(e)}")


def _find_relevant_files(
    all_files: List[str], 
    channel: str,
    prefer_processed: bool
) -> List[str]:
    """查找相关的数据文件"""
    relevant = []
    
    for file_path in all_files:
        filename = os.path.basename(file_path).lower()
        
        # 跳过隐藏文件和元数据
        if filename.startswith('.') or filename.startswith('__'):
            continue
        
        # 跳过文档文件
        if any(filename.startswith(prefix) for prefix in ['readme', 'info', 'documentation']):
            continue
        
        # 检查文件扩展名
        if not any(filename.endswith(ext) for ext in ['.csv', '.txt', '.xlsx']):
            continue
        
        # 跳过 Turbidity（浊度）数据 - nanoDSF 分析不需要
        if 'turbidity' in filename:
            continue
        
        # 通道过滤
        channel_lower = channel.lower()
        if 'ratio' in channel_lower:
            if '330' in filename and '350' not in filename:
                continue
            if '350' in filename and 'ratio' not in filename and '330' not in filename:
                continue
        elif '350' in channel_lower and '330' not in channel_lower:
            if '330' in filename and '350' not in filename:
                continue
            if 'ratio' in filename:
                continue
        elif '330' in channel_lower:
            if '350' in filename and '330' not in filename:
                continue
            if 'ratio' in filename:
                continue
        
        # 处理/原始数据优先级
        if prefer_processed:
            if 'raw' in filename and 'processed' not in filename:
                continue
        else:
            if 'processed' in filename:
                continue
        
        relevant.append(file_path)
    
    return relevant


__all__ = [
    'detect_instrument_type',
    'parse_instrument_file',
    'parse_zip_file',
    'parse_prometheus_csv',
    'parse_tycho_nt6_csv',
    'parse_tycho_nt6_excel',
    'is_prometheus_file',
    'is_tycho_file',
]

