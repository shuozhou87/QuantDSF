#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic Analysis Layout
======================
基础 Tm 分析页面布局
"""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components import create_results_table, create_curve_plot


def _create_empty_figure(message: str):
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray"),
    )
    fig.update_layout(template="plotly_white")
    return fig


def create_basic_analysis_layout() -> html.Div:
    """创建基础分析页面布局"""
    return html.Div([
        # 结果表格
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                "Analysis Results",
                dbc.Badge(id="sample-count-badge", color="info", className="ms-2")
            ]),
            dbc.CardBody([
                html.Div(id="results-table-container")
            ])
        ], className="shadow-sm mb-4"),
        
        # 可视化区域
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📈 Melting Curves"),
                    dbc.CardBody([
                        dcc.Graph(
                            id='melting-curves-plot',
                            style={'height': '400px'}
                        )
                    ])
                ], className="shadow-sm")
            ], md=12),
        ]),
        html.Div(
            dcc.Graph(
                id='tm-distribution-plot',
                figure=_create_empty_figure("Tm Distribution is temporarily unavailable")
            ),
            id='tm-dist-column',
            style={'display': 'none'}
        ),
    ], className="p-3")
