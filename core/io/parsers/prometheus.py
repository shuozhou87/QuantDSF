#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prometheus NT.48 Data Parser
=============================
Prometheus NT.48 数据解析器

支持 Prometheus Panta/NT.48 格式的 CSV 文件
从 V1 迁移，保持核心算法不变
"""
import os
import io
import pandas as pd
import numpy as np
from typing import Tuple, Union
from core.utils.parser import clean_sample_name


def parse_prometheus_csv(
    file_content: Union[str, bytes], 
    file_path: str
) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    解析 Prometheus nanoDSF CSV 文件
    
    Args:
        file_content: 原始文件内容
        file_path: 文件路径
    
    Returns:
        (temperature_array, fluorescence_array, capillary_id) 元组
    """
    if isinstance(file_content, bytes):
        df = pd.read_csv(io.BytesIO(file_content), sep='\t')
    else:
        df = pd.read_csv(io.StringIO(file_content), sep='\t')
    
    df.columns = [c.strip() for c in df.columns]
    
    # 提取温度和荧光数据
    T = df['T[°C]'].values
    F = df[df.columns[1]].values  # 第二列

    # 从文件名提取毛细管 ID，并清理样本名称
    raw_filename = os.path.splitext(os.path.basename(file_path))[0]
    capillary_id = clean_sample_name(raw_filename)

    return T, F, capillary_id


def is_prometheus_file(file_content: Union[bytes, str], file_path: str) -> bool:
    """
    检测文件是否为 Prometheus 格式
    
    Args:
        file_content: 文件内容
        file_path: 文件路径
    
    Returns:
        是否为 Prometheus 格式
    """
    filename = os.path.basename(file_path).lower()
    
    # 排除文档和元数据文件
    if any(filename.startswith(prefix) for prefix in ['readme', 'info', 'documentation', 'metadata']):
        return False
    
    # 检查文件名模式
    if filename.endswith('raw.csv') or filename.endswith('processed.csv'):
        return True
    
    # 检查文件内容
    try:
        if hasattr(file_content, 'read'):
            content = file_content.read(1024).decode('utf-8', errors='ignore')
            file_content.seek(0)
        elif isinstance(file_content, bytes):
            content = file_content[:1024].decode('utf-8', errors='ignore')
        else:
            content = file_content[:1024]
        
        lines = content.split('\n')[:10]
        
        for line in lines:
            if 'T[°C]' in line:
                return True
            if any(pattern in line.lower() for pattern in ['ratio', '350nm', '330nm', 'unfolding']):
                if '\t' in line:  # Tab 分隔
                    return True
                    
    except Exception:
        pass
    
    return False

