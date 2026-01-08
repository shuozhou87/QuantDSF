#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel Exporter
===============
Excel 格式导出
"""

import io
from typing import List, Optional
import pandas as pd

from ...models import TmResult, VanHoffResult, CapillaryData


def export_to_excel(
    capillaries: List[CapillaryData],
    tm_results: List[TmResult],
    vanthoff_result: Optional[VanHoffResult] = None
) -> bytes:
    """
    导出结果为 Excel
    
    Args:
        capillaries: 毛细管数据列表
        tm_results: Tm 结果列表
        vanthoff_result: Van't Hoff 结果（可选）
    
    Returns:
        Excel 文件字节
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Tm 结果 sheet
        data = []
        for cap, tm in zip(capillaries, tm_results):
            row = {
                'Sample': cap.name,
                'Concentration (M)': cap.concentration if cap.concentration else None,
                'Tm (°C)': tm.tm if not pd.isna(tm.tm) else None,
                'R²': tm.r_squared,
                'Method': tm.method.value,
                'Status': tm.quality_flag,
                'Source File': cap.source_file
            }
            data.append(row)
        
        df_tm = pd.DataFrame(data)
        df_tm.to_excel(writer, sheet_name='Tm Results', index=False)
        
        # Van't Hoff 结果 sheet
        if vanthoff_result:
            vh_data = {
                'Parameter': [
                    'R²',
                    'n_points',
                    'ΔH (J/mol)',
                    'ΔS (J/mol/K)',
                    'KD at 298K (M)',
                    'KD at 310K (M)',
                    'Reliability 298K',
                    'Reliability 310K'
                ],
                'Value': [
                    vanthoff_result.r_squared,
                    vanthoff_result.n_points,
                    vanthoff_result.thermodynamics.delta_h,
                    vanthoff_result.thermodynamics.delta_s,
                    vanthoff_result.kd_298k,
                    vanthoff_result.kd_310k,
                    vanthoff_result.reliability_298k.level,
                    vanthoff_result.reliability_310k.level
                ]
            }
            df_vh = pd.DataFrame(vh_data)
            df_vh.to_excel(writer, sheet_name='Van\'t Hoff', index=False)
    
    return output.getvalue()


