#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export Callbacks
=================
导出相关回调
"""

from dash import Dash, callback, Input, Output, State, dcc


def register_export_callbacks(app: Dash) -> None:
    """注册导出相关回调"""
    
    @app.callback(
        Output('download-vanthoff-csv', 'data'),
        Input('download-vanthoff-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_vanthoff_summary(n_clicks):
        """下载 Van't Hoff 分析摘要"""
        # TODO: 实现完整的导出逻辑
        
        csv_content = "Parameter,Value\nR²,0.985\nΔH (kJ/mol),-118.9\n"
        
        return dcc.send_string(csv_content, "vanthoff_summary.csv")


