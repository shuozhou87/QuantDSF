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
    """创建Basic Analysis初始布局 - Split-View架构: 表格区(上) + 图表区(下)"""
    return html.Div([
        # ==================== TABLE AREA (Top ~35vh) ====================
        html.Div([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-table me-2"),
                    "Analysis Results",
                    dbc.Badge("0 samples", id="sample-count-badge", color="secondary", className="ms-2")
                ]),
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-results",
                        type="default",
                        fullscreen=False,
                        children=html.Div(id="results-table-container", children=[
                            html.P("Waiting for data...", className="text-muted text-center py-5")
                        ]),
                        overlay_style={"visibility": "visible", "opacity": 0.7, "filter": "blur(2px)"},
                        custom_spinner=html.Div([
                            dbc.Spinner(color="primary", size="lg", spinner_style={"width": "4rem", "height": "4rem"}),
                            html.Div(id="loading-status-message",
                                    children="Analyzing data...",
                                    className="text-primary fw-bold mt-3",
                                    style={"fontSize": "1.3rem"})
                        ], className="text-center", style={"paddingTop": "50px"})
                    )
                ], style={"maxHeight": "28vh", "overflowY": "auto"})
            ], className="shadow-sm"),
        ], style={"marginBottom": "1rem"}),

        # ==================== PLOT AREA (Bottom ~60vh) ====================
        html.Div([
            dbc.Card([
                dbc.CardBody([
                    dbc.Tabs([
                        # Tab 1: Melting Curves
                        dbc.Tab(
                            label="📈 Melting Curves",
                            tab_id="plot-melting",
                            children=html.Div([
                                dcc.Graph(
                                    id='melting-curves-plot',
                                    figure=_create_empty_figure("Upload data and run analysis"),
                                    style={'height': '55vh'}
                                )
                            ], id='melting-curves-column')
                        ),
                        # Tab 2: First Derivative (conditional)
                        dbc.Tab(
                            label="📉 First Derivative",
                            tab_id="plot-derivative",
                            children=html.Div([
                                dcc.Graph(
                                    id='derivative-curves-plot',
                                    figure=_create_empty_figure("Select First Derivative method"),
                                    style={'height': '55vh'}
                                )
                            ], id='derivative-panel')
                        ),
                    ], id="basic-plot-tabs", active_tab="plot-melting"),
                    html.Div(
                        dcc.Graph(
                            id='tm-distribution-plot',
                            figure=_create_empty_figure("Tm Distribution is temporarily unavailable"),
                        ),
                        id='tm-dist-column',
                        style={'display': 'none'}
                    )
                ], className="p-2")
            ], className="shadow-sm"),
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
        dcc.Store(id='dose-response-store', storage_type='memory'),
        dcc.Store(id='thermodynamics-store', storage_type='memory'),

        # 下载组件
        dcc.Download(id='download-export-package'),

        # Export loading overlay (全屏加载提示)
        dcc.Loading(
            id="loading-export",
            type="default",
            fullscreen=True,
            children=html.Div(id='export-loading-trigger', style={'display': 'none'}),
            overlay_style={
                "visibility": "visible",
                "backgroundColor": "rgba(240, 240, 240, 0.95)",  # 更不透明的灰色背景
                "zIndex": "9999"
            },
            custom_spinner=html.Div([
                dbc.Spinner(color="primary", size="lg", spinner_style={"width": "4rem", "height": "4rem"}),
                html.Div([
                    html.Div("📄 Generating PDF Report",
                            style={
                                "fontSize": "1.6rem",
                                "fontWeight": "600",
                                "color": "#2c3e50",  # 深灰/黑色
                                "marginTop": "1.5rem",
                                "marginBottom": "0.5rem"
                            }),
                    html.Div("Please wait while we compile your results...",
                            style={
                                "fontSize": "1rem",
                                "color": "#7f8c8d",  # 中灰色
                                "fontWeight": "normal"
                            })
                ])
            ], className="text-center", style={"paddingTop": "20vh"})
        ),

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
                # Page title removed (moved to Navbar)
                
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
