#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tycho NT.6 Data Parser
=======================
Tycho NT.6 数据解析器

支持 Tycho NT.6 格式的 CSV 和 Excel 文件
从 V1 迁移，保持核心算法不变
"""
import os
import io
import re
import pandas as pd
import numpy as np
from typing import Tuple, List, Union, Optional, Dict


def parse_tycho_nt6_csv(
    file_content: Union[str, bytes], 
    file_path: str
) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    解析 Tycho NT.6 CSV 文件
    
    Args:
        file_content: 原始文件内容
        file_path: 文件路径
    
    Returns:
        (temperature_array, fluorescence_array, capillary_id) 元组
    """
    if isinstance(file_content, bytes):
        content_str = file_content.decode('utf-8', errors='ignore')
    else:
        content_str = file_content
    
    for sep in [',', '\t', ';']:
        try:
            df = pd.read_csv(io.StringIO(content_str), sep=sep)
            df.columns = [str(c).strip() for c in df.columns]
            
            if len(df.columns) < 2:
                continue
            
            # 查找温度列
            temp_col = _find_temperature_column(df.columns)
            if temp_col is None:
                temp_col = df.columns[0]
            
            # 查找荧光列
            fluor_col = _find_fluorescence_column(df.columns, temp_col)
            if fluor_col is None:
                available_cols = [c for c in df.columns if c != temp_col]
                if available_cols:
                    fluor_col = available_cols[0]
                else:
                    fluor_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            
            T = pd.to_numeric(df[temp_col], errors='coerce').values
            F = pd.to_numeric(df[fluor_col], errors='coerce').values
            
            valid_mask = ~(np.isnan(T) | np.isnan(F))
            T = T[valid_mask]
            F = F[valid_mask]
            
            if len(T) >= 10 and len(F) >= 10:
                capillary_id = os.path.splitext(os.path.basename(file_path))[0]
                return T, F, capillary_id
                
        except Exception:
            continue
    
    raise ValueError(f"无法解析 Tycho NT.6 文件: {file_path}")


def parse_tycho_nt6_excel(
    file_content: bytes, 
    file_path: str, 
    target_channel: Optional[str] = None
) -> List[Tuple[np.ndarray, np.ndarray, str]]:
    """
    解析 Tycho NT.6 Excel 文件
    
    NT.6 Excel 格式:
    - Results 工作表: 毛细管标签和摘要数据
    - Profiles_raw 工作表: 温度和荧光数据
    
    Args:
        file_content: 原始文件内容 (bytes)
        file_path: 文件路径
        target_channel: 要提取的特定通道
    
    Returns:
        (temperature_array, fluorescence_array, capillary_id) 元组列表
    """
    results = []
    
    try:
        excel_file = pd.ExcelFile(io.BytesIO(file_content))
        
        if 'Results' not in excel_file.sheet_names or 'Profiles_raw' not in excel_file.sheet_names:
            raise ValueError("不是有效的 Tycho NT.6 Excel 文件 - 缺少必需的工作表")
        
        # 读取毛细管标签
        df_results = pd.read_excel(excel_file, sheet_name='Results', header=None)
        capillary_labels = {}
        
        for i in range(2, min(20, len(df_results))):
            try:
                cap_num_val = df_results.iloc[i, 1]
                cap_label_val = df_results.iloc[i, 2]
                
                if pd.notna(cap_num_val) and pd.notna(cap_label_val) and str(cap_num_val) != '#':
                    cap_num = int(float(cap_num_val))
                    capillary_labels[cap_num] = str(cap_label_val)
            except (ValueError, TypeError):
                continue
        
        # 读取原始数据
        df_raw = pd.read_excel(excel_file, sheet_name='Profiles_raw', header=None)
        
        data_start_row = 6
        temp_data = pd.to_numeric(df_raw.iloc[data_start_row+1:, 1], errors='coerce').dropna()
        
        if len(temp_data) < 10:
            raise ValueError("温度数据点不足")
        
        # 定义通道组
        channel_groups = {
            'ratio': {'start_col': 2, 'end_col': 7, 'channel_name': '350/330 nm ratio'},
            '330nm': {'start_col': 9, 'end_col': 14, 'channel_name': '330 nm'},
            '350nm': {'start_col': 16, 'end_col': 21, 'channel_name': '350 nm'}
        }
        
        # 过滤通道
        if target_channel:
            channel_mapping = {
                '350/330 nm ratio': ['ratio'],
                'ratio': ['ratio'],
                '350 nm': ['350nm'],
                '350nm': ['350nm'],
                '330 nm': ['330nm'],
                '330nm': ['330nm'],
            }
            allowed_channels = channel_mapping.get(target_channel, list(channel_groups.keys()))
            filtered_channel_groups = {k: v for k, v in channel_groups.items() if k in allowed_channels}
        else:
            filtered_channel_groups = channel_groups
        
        # 提取数据
        for channel_key, channel_info in filtered_channel_groups.items():
            for cap_idx in range(6):
                cap_num = cap_idx + 1
                col_idx = channel_info['start_col'] + cap_idx
                
                if col_idx >= df_raw.shape[1]:
                    continue
                
                fluor_data = pd.to_numeric(
                    df_raw.iloc[data_start_row+1:data_start_row+1+len(temp_data), col_idx], 
                    errors='coerce'
                )
                
                valid_mask = ~(np.isnan(temp_data.values) | np.isnan(fluor_data.values))
                T_clean = temp_data.values[valid_mask]
                F_clean = fluor_data.values[valid_mask]
                
                if len(T_clean) >= 10:
                    cap_label = capillary_labels.get(cap_num, f"Cap{cap_num}")
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    capillary_id = f"{base_name}_{cap_label}_{channel_info['channel_name']}"
                    
                    results.append((T_clean, F_clean, capillary_id))
                    
    except Exception as e:
        raise ValueError(f"无法解析 Tycho NT.6 Excel 文件: {file_path} - {e}")
    
    if not results:
        raise ValueError(f"在 Tycho NT.6 文件中未找到有效数据: {file_path}")
    
    return results


def is_tycho_file(file_content: Union[bytes, str], file_path: str) -> bool:
    """
    检测文件是否为 Tycho NT.6 格式
    
    Args:
        file_content: 文件内容
        file_path: 文件路径
    
    Returns:
        是否为 Tycho 格式
    """
    filename = os.path.basename(file_path).lower()
    
    # Excel 文件特殊处理
    if filename.endswith('.xlsx'):
        try:
            content = file_content if isinstance(file_content, bytes) else file_content.encode()
            excel_file = pd.ExcelFile(io.BytesIO(content))
            
            sheet_names = excel_file.sheet_names
            if ('Results' in sheet_names and 'Profiles_raw' in sheet_names and 
                'Profiles_smoothed' in sheet_names and 'Profiles_derivative' in sheet_names):
                return True
            
            return False
            
        except Exception:
            return False
    
    # CSV/TXT 文件
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
            if any(pattern in line.lower() for pattern in [
                'temperature', 'temp', 'fluorescence', 'channel',
                'tycho', 'nt.6', 'nt6', 'brightness'
            ]):
                return True
                
    except Exception:
        pass
    
    return False


def _find_temperature_column(columns: list) -> Optional[str]:
    """查找温度列"""
    temp_patterns = [
        r'temp.*[°c]', r'temperature.*[°c]', r'temp', r'temperature',
        r't\[.*°c.*\]', r't\[.*c.*\]', r'°c', r'celsius'
    ]
    
    for col in columns:
        col_lower = str(col).lower()
        for pattern in temp_patterns:
            if re.search(pattern, col_lower):
                return col
    return None


def _find_fluorescence_column(columns: list, temp_col: str) -> Optional[str]:
    """查找荧光列"""
    fluor_patterns = [
        r'fluor', r'signal', r'intensity', r'ratio',
        r'350.*330', r'330.*350', r'f\d+', r'channel'
    ]
    
    for col in columns:
        if col == temp_col:
            continue
        col_lower = str(col).lower()
        for pattern in fluor_patterns:
            if re.search(pattern, col_lower):
                return col
    return None

