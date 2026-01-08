#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Data Table Component
=====================
数据表格组件
"""

from dash import html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from typing import List, Dict, Any


def create_results_table(data: List[Dict[str, Any]], columns: List[str] = None) -> dash_table.DataTable:
    """
    创建结果表格
    
    Args:
        data: 数据列表
        columns: 要显示的列（默认全部）
    
    Returns:
        DataTable 组件
    """
    if not data:
        return html.Div("No data available", className="text-muted text-center p-3")
    
    df = pd.DataFrame(data)
    
    if columns:
        df = df[columns]
    
    return dash_table.DataTable(
        id='results-table',
        columns=[{'name': col, 'id': col} for col in df.columns],
        data=df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontFamily': 'Segoe UI, sans-serif'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'borderBottom': '2px solid #dee2e6'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            },
            {
                'if': {'filter_query': '{Status} contains "⚠️"'},
                'backgroundColor': '#fff3cd'
            },
            {
                'if': {'filter_query': '{Status} contains "❌"'},
                'backgroundColor': '#f8d7da'
            }
        ],
        row_selectable='multi',
        selected_rows=[],
        page_size=15,
        filter_action='native',
        sort_action='native',
    )


def create_selection_table(
    data: List[Dict[str, Any]],
    id_prefix: str,
    selectable: bool = True
) -> dash_table.DataTable:
    """
    创建可选择的数据表格
    
    Args:
        data: 数据列表
        id_prefix: ID 前缀
        selectable: 是否可选择
    
    Returns:
        DataTable 组件
    """
    if not data:
        return html.Div("No data available", className="text-muted text-center p-3")
    
    df = pd.DataFrame(data)
    
    return dash_table.DataTable(
        id=f'{id_prefix}-table',
        columns=[{'name': col, 'id': col} for col in df.columns],
        data=df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontSize': '13px'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold'
        },
        row_selectable='multi' if selectable else False,
        selected_rows=list(range(len(data))),  # 默认全选
        page_size=10,
    )


