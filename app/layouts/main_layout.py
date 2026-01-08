#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Application Layout
========================
主应用布局 - 导航栏、侧边栏、内容区
"""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..components import create_sidebar, create_navbar


def _create_empty_figure(message: str):
    """创建空图表占位"""
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray")
    )
    fig.update_layout(template='plotly_white')
    return fig


def _create_basic_analysis_initial_layout():
    """创建Basic Analysis初始布局 - 固定结构,不再动态变化"""
    return html.Div([
        # 结果表格
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                "Analysis Results",
                dbc.Badge("0 samples", id="sample-count-badge", color="secondary", className="ms-2")
            ]),
            dbc.CardBody([
                html.Div(id="results-table-container", children=[
                    html.P("Waiting for data...", className="text-muted text-center py-5")
                ])
            ])
        ], className="shadow-sm mb-4"),

        # 图表区域 - 固定布局
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📈 Melting Curves"),
                    dbc.CardBody([
                        dcc.Graph(
                            id='melting-curves-plot',
                            figure=_create_empty_figure("Upload data and run analysis"),
                            style={'height': '400px'}
                        )
                    ])
                ], className="shadow-sm mb-3"),

                # First Derivative曲线面板 - 仅FD方法时显示
                dbc.Card([
                    dbc.CardHeader("📉 First Derivative Curves"),
                    dbc.CardBody([
                        dcc.Graph(
                            id='derivative-curves-plot',
                            figure=_create_empty_figure("Select First Derivative method"),
                            style={'height': '400px'}
                        )
                    ])
                ], id='derivative-panel', className="shadow-sm", style={'display': 'none'}),
            ], id='melting-curves-column', md=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Tm Distribution"),
                    dbc.CardBody([
                        dcc.Graph(
                            id='tm-distribution-plot',
                            figure=_create_empty_figure("Upload data and run analysis"),
                            style={'height': '400px'}
                        )
                    ])
                ], className="shadow-sm")
            ], id='tm-dist-column', md=6),
        ]),
    ], className="p-3")


def create_main_layout() -> dbc.Container:
    """
    创建主应用布局
    
    结构:
    ┌─────────────────────────────────────────┐
    │              Navbar                      │
    ├───────────┬─────────────────────────────┤
    │           │                              │
    │  Sidebar  │        Content Area          │
    │           │          (Tabs)              │
    │           │                              │
    └───────────┴─────────────────────────────┘
    """
    return dbc.Container([
        # 数据存储
        dcc.Store(id='app-state-store', storage_type='memory'),
        dcc.Store(id='config-store', storage_type='memory'),
        dcc.Store(id='analysis-results-store', storage_type='memory'),
        
        # 导航栏
        create_navbar(),
        
        # 主内容区
        dbc.Row([
            # 侧边栏
            dbc.Col(
                create_sidebar(),
                md=3,
                className="mb-4"
            ),
            
            # 内容区
            dbc.Col([
                # 页面标题
                html.Div([
                    html.H3([
                        html.I(className="fas fa-chart-line me-2 text-primary"),
                        "nanoDSF Analysis Platform"
                    ], className="mb-1"),
                    html.P(
                        "High-throughput thermal stability and binding thermodynamics analysis",
                        className="text-muted mb-4"
                    )
                ]),
                
                # 标签页
                dbc.Tabs([
                    dbc.Tab(
                        label="🧪 Basic Analysis",
                        tab_id="basic",
                        children=_create_basic_analysis_initial_layout()
                    ),
                    dbc.Tab(
                        label="🔬 Thermodynamic Analysis",
                        tab_id="thermo",
                        children=html.Div(id="thermo-analysis-content")
                    ),
                    dbc.Tab(
                        label="📈 Dose-Response",
                        tab_id="dose",
                        children=html.Div(id="dose-response-content")
                    ),
                ], id="main-tabs", active_tab="basic", className="mb-3"),
                
            ], md=9),
        ]),
        
        # 页脚
        html.Footer([
            html.Hr(),
            html.P([
                "QuantDSF | Built with ",
                html.I(className="fas fa-heart text-danger"),
                " using Dash & Plotly"
            ], className="text-center text-muted small")
        ], className="mt-4")
        
    ], fluid=True, className="px-4")

