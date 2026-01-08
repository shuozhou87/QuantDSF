#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parser Utilities
=================
数据解析工具函数

支持从文件名中提取浓度信息
"""
import re
from typing import Optional, List, Tuple


# 单位 + 浓度的正则模式
UNIT_PATTERN = re.compile(
    r'([-+]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*(?:([fFpPnNuUµμmMcCdDkKhH]?)[mM])'
)

# 科学计数法模式（无单位）
SCIENTIFIC_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?[eE][+-]?\d+)'
)


def _unit_multiplier(prefix: str) -> Optional[float]:
    """返回单位前缀的倍数因子"""
    if prefix is None:
        return 1.0
    prefix = prefix.strip()
    if prefix == "":
        return 1.0
    prefix = prefix.lower()
    mapping = {
        'f': 1e-15,  # femto
        'p': 1e-12,  # pico
        'n': 1e-9,   # nano
        'u': 1e-6,   # micro
        'µ': 1e-6,   # micro (Unicode)
        'μ': 1e-6,   # micro (Greek mu)
        'm': 1e-3,   # milli
        'c': 1e-2,   # centi
        'd': 1e-1,   # deci
        'h': 1e2,    # hecto
        'k': 1e3,    # kilo
    }
    return mapping.get(prefix)


def _extract_unit_concentrations(text: str) -> List[Tuple[float, int]]:
    """
    从文本中提取带单位的浓度值
    
    Returns:
        List of (concentration, position) tuples
    """
    candidates = []
    for match in UNIT_PATTERN.finditer(text):
        token = re.sub(r'\s+', '', match.group(0)).lower()
        # 排除波长标记
        if token in {"330nm", "350nm"}:
            continue
        value_str = match.group(1)
        prefix = match.group(2)
        try:
            value = float(value_str)
        except (TypeError, ValueError):
            continue
        multiplier = _unit_multiplier(prefix)
        if multiplier is None:
            continue
        conc = value * multiplier
        if conc <= 0:
            continue
        # 合理范围：1e-12 M 到 1 M
        if 1e-12 <= conc <= 1.0:
            candidates.append((conc, match.start()))
    return candidates


def _extract_scientific_concentrations(text: str) -> List[Tuple[float, int]]:
    """
    从文本中提取科学计数法浓度（无单位，假设单位是 M）
    
    Returns:
        List of (concentration, position) tuples
    """
    candidates = []
    for match in SCIENTIFIC_PATTERN.finditer(text):
        try:
            value = float(match.group(1))
            # 科学计数法的浓度通常在合理范围内
            if 1e-12 <= value <= 1.0:
                candidates.append((value, match.start()))
        except (TypeError, ValueError):
            continue
    return candidates


def parse_concentration(filename: str) -> Optional[float]:
    """
    从文件名中提取浓度值
    
    策略：
    1. 优先提取科学计数法浓度（通常是变化的 analyte 浓度）
    2. 如果有 '+' 或 '_' 分隔符，优先使用后面部分的浓度
    3. 带单位的浓度（如 1uM）通常是恒定的 ligand 浓度，优先级较低
    
    支持多种格式：
    - 科学计数法: "1.00E-4", "5E-5" (highest priority)
    - 带单位: "125uM", "0.5 µM", "3mM"
    - 小数格式: "0.00025", "0.000125"
    
    Args:
        filename: 可能包含浓度的文件名
    
    Returns:
        提取的浓度值（摩尔），如果未找到则返回 None
    """
    if not filename:
        return None
    
    # 排除波长标记文件
    lowered = filename.lower()
    if lowered in ("330 nm", "350 nm"):
        return None
    
    # 策略 1：优先在 '+' 或 '_' 后面查找科学计数法浓度
    # 这种格式常见于 "1uM TNFa+Zn_1.00E-4_Ratio_unfolding_raw"
    
    # 查找所有分隔符位置
    separators = []
    for i, char in enumerate(filename):
        if char in '+_':
            separators.append(i)
    
    # 提取科学计数法浓度
    scientific_concs = _extract_scientific_concentrations(filename)
    
    if scientific_concs:
        # 如果有分隔符，优先选择分隔符后面的科学计数法浓度
        if separators:
            # 找到在某个分隔符之后的浓度
            for conc, pos in scientific_concs:
                for sep_pos in separators:
                    if pos > sep_pos:
                        return conc
        
        # 如果没有分隔符或分隔符后没有科学计数法，返回第一个科学计数法浓度
        # 但要确保它不是来自带单位浓度的一部分
        unit_concs = _extract_unit_concentrations(filename)
        unit_positions = set(pos for _, pos in unit_concs)
        
        for conc, pos in scientific_concs:
            # 检查这个位置是否已经被带单位的浓度覆盖
            is_part_of_unit = False
            for unit_conc, unit_pos in unit_concs:
                # 如果科学计数法的位置在带单位浓度的范围内，跳过
                if unit_pos <= pos <= unit_pos + 20:  # 假设单位浓度字符串不超过20字符
                    is_part_of_unit = True
                    break
            
            if not is_part_of_unit:
                return conc
    
    # 策略 2：处理 '+' 后面的部分
    if '+' in filename:
        after_plus = filename.split('+')[-1]
        # 在 '+' 后面查找科学计数法
        sci_after_plus = _extract_scientific_concentrations(after_plus)
        if sci_after_plus:
            return sci_after_plus[0][0]
        
        # 在 '+' 后面查找带单位的浓度
        unit_after_plus = _extract_unit_concentrations(after_plus)
        if unit_after_plus:
            return unit_after_plus[-1][0]  # 取最后一个
    
    # 策略 3：回退到带单位的浓度
    unit_concs = _extract_unit_concentrations(filename)
    if unit_concs:
        # 如果有多个，取最后一个（通常是变化的浓度）
        return unit_concs[-1][0]
    
    # 策略 4：尝试简单的小数格式
    decimal_match = re.search(r'(\d+\.\d{3,})', filename)
    if decimal_match:
        try:
            value = float(decimal_match.group(1))
            if 1e-9 <= value <= 1e-2:
                return value
        except ValueError:
            pass
    
    return None


def parse_all_concentrations(filename: str) -> List[float]:
    """
    从文件名中提取所有可能的浓度值
    
    用于调试或让用户选择正确的浓度
    
    Args:
        filename: 文件名
    
    Returns:
        所有检测到的浓度值列表
    """
    if not filename:
        return []
    
    concentrations = []
    
    # 提取带单位的浓度
    unit_concs = _extract_unit_concentrations(filename)
    for conc, _ in unit_concs:
        if conc not in concentrations:
            concentrations.append(conc)
    
    # 提取科学计数法浓度
    sci_concs = _extract_scientific_concentrations(filename)
    for conc, _ in sci_concs:
        if conc not in concentrations:
            concentrations.append(conc)
    
    return concentrations


def format_concentration(conc: float) -> str:
    """
    将浓度值格式化为人类可读的字符串

    Args:
        conc: 浓度值（摩尔）

    Returns:
        格式化的字符串，如 "1.5 µM", "25 nM"
    """
    if conc is None:
        return "N/A"

    if conc >= 1e-3:
        return f"{conc * 1e3:.2f} mM"
    elif conc >= 1e-6:
        return f"{conc * 1e6:.2f} µM"
    elif conc >= 1e-9:
        return f"{conc * 1e9:.2f} nM"
    elif conc >= 1e-12:
        return f"{conc * 1e12:.2f} pM"
    else:
        return f"{conc:.2e} M"


def clean_sample_name(filename: str) -> str:
    """
    清理样本名称，移除冗余的文件名信息

    从文件名中移除：
    - 浓度信息（已在 Concentration 列显示）
    - 占位浓度 "_0_"
    - 波长标记（"_330 nm", "_350 nm", "_ratio"）
    - 文件类型标记（"_unfolding", "_raw", "_processed"）
    - 文件扩展名

    例如：
    "XBB_1.25E-5_0_330 nm_unfolding_raw" -> "XBB"
    "TNFa_1uM_350nm_processed" -> "TNFa"
    "Sample1_2.5E-6_ratio_raw" -> "Sample1"

    Args:
        filename: 原始文件名

    Returns:
        清理后的样本名称
    """
    if not filename:
        return filename

    # 移除文件扩展名
    name = filename
    for ext in ['.csv', '.txt', '.xlsx', '.xls']:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
            break

    # 定义需要移除的模式（按顺序）
    patterns_to_remove = [
        # 波长标记 (先处理这些，因为它们更具体)
        # 先处理复合模式 (如 "350/330 nm ratio")
        r'[_\-\s]*350/330\s*nm\s*ratio[_\-\s]*',
        r'[_\-\s]*330/350\s*nm\s*ratio[_\-\s]*',
        r'[_\-\s]*350\s*/\s*330\s*nm[_\-\s]*',
        r'[_\-\s]*330\s*/\s*350\s*nm[_\-\s]*',
        # 单独的波长标记
        r'[_\-\s]*330\s*nm[_\-\s]*',
        r'[_\-\s]*350\s*nm[_\-\s]*',
        r'[_\-\s]*ratio[_\-\s]*',
        # 浓度模式（科学计数法）
        r'[_\-\s]*\d+\.?\d*[eE][+-]?\d+[_\-\s]*',
        # 浓度模式（带单位）
        r'[_\-\s]*\d+\.?\d*\s*[fFpPnNuUµμmM]?[mM][_\-\s]*',
        # 占位浓度 "_0_" 或类似模式
        r'[_\-\s]+0[_\-\s]+',
        # 移除独立的小数浓度值（如 "_0.05_"）
        r'[_\-\s]+\d*\.\d+[_\-\s]+',
        # 文件类型标记 (注意前后都可能有分隔符)
        r'[_\-\s]*unfolding[_\-\s]*',
        r'[_\-\s]*raw[_\-\s]*',
        r'[_\-\s]*processed[_\-\s]*',
        r'[_\-\s]*smoothed[_\-\s]*',
        r'[_\-\s]*derivative[_\-\s]*',
        r'[_\-\s]*firstderivative[_\-\s]*',
    ]

    # 应用所有移除模式（多次迭代确保彻底清理）
    for _ in range(2):  # 运行两次以处理嵌套模式
        for pattern in patterns_to_remove:
            name = re.sub(pattern, '_', name, flags=re.IGNORECASE)

    # 清理多余的分隔符
    # 移除开头和结尾的分隔符
    name = name.strip('_- ')

    # 将多个连续分隔符替换为单个下划线
    name = re.sub(r'[_\-\s]+', '_', name)

    # 再次清理边缘
    name = name.strip('_- ')

    # 如果清理后为空，返回原始文件名
    if not name:
        return filename

    return name

