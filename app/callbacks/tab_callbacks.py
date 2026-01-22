#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tab Content Callbacks
======================
标签页内容切换回调
"""

from dash import Dash, callback, Input, Output, html, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc
import numpy as np


def register_tab_callbacks(app: Dash) -> None:
    """注册标签页相关回调"""

    # Basic Analysis tab使用固定布局(在main_layout中定义),不需要动态渲染

    @app.callback(
        Output('sfq-collapse', 'is_open'),
        Input('sfq-card-header', 'n_clicks'),
        State('sfq-collapse', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_sfq_collapse(n_clicks, is_open):
        """Toggle SFQ analysis card collapse"""
        if n_clicks:
            return not is_open
        return is_open

    # Note: Basic Analysis tab now uses tabbed plot layout instead of side-by-side.
    # The old update_layout_based_on_data callback is no longer needed.
    
    @app.callback(
        Output('thermo-analysis-content', 'children'),
        Input('main-tabs', 'active_tab'),
        State('analysis-results-store', 'data')
    )
    def render_thermo_tab(active_tab, results_data):
        """渲染热力学分析标签页"""
        if active_tab != 'thermo':
            return no_update
        
        return _create_thermo_analysis_content(results_data)
    
    @app.callback(
        Output('dose-response-content', 'children'),
        Input('main-tabs', 'active_tab'),
        State('analysis-results-store', 'data')
    )
    def render_dose_tab(active_tab, results_data):
        """渲染剂量响应标签页"""
        print(f"[DEBUG] render_dose_tab called with active_tab={active_tab}")
        if active_tab != 'dose':
            return no_update

        content = _create_dose_response_content(results_data)
        print(f"[DEBUG] Returning dose-response content, type={type(content)}")
        return content


def _create_basic_analysis_content(results_data) -> html.Div:
    """创建基础分析内容"""
    
    # 如果没有数据，显示占位内容
    if not results_data or not results_data.get('results'):
        return html.Div([
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                "Please upload data files and click 'Run Analysis' to start"
            ], color="info", className="mb-4"),
            
            # 空表格和图表占位
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-table me-2"),
                    "Analysis Results",
                    dbc.Badge("0 samples", color="secondary", className="ms-2")
                ]),
                dbc.CardBody([
                    html.Div(id="results-table-container", children=[
                        html.P("Waiting for data...", className="text-muted text-center py-5")
                    ])
                ])
            ], className="shadow-sm mb-4"),
            
            # 图表区域
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📈 Melting Curves"),
                        dbc.CardBody([
                            dcc.Graph(
                                id='melting-curves-plot',
                                figure=_create_empty_figure("Upload data to see melting curves"),
                                style={'height': '400px'}
                            )
                        ])
                    ], className="shadow-sm")
                ], id='melting-curves-column', md=6),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📊 Tm Distribution"),
                        dbc.CardBody([
                            dcc.Graph(
                                id='tm-distribution-plot',
                                figure=_create_empty_figure("Upload data to see Tm distribution"),
                                style={'height': '400px'}
                            )
                        ])
                    ], className="shadow-sm")
                ], id='tm-dist-column', md=6),
            ]),
            
        ], className="p-3")
    
    # 有数据时显示结果 - 使用固定布局,由单独的回调控制显示/隐藏
    results = results_data['results']
    session_id = results_data.get('session_id')

    return html.Div([
        dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"Analysis complete! {len(results)} samples processed",
            f" (Session #{session_id})" if session_id else ""
        ], color="success", className="mb-4"),

        # 结果表格
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                "Analysis Results",
                dbc.Badge(f"{len(results)} samples", color="info", className="ms-2")
            ]),
            dbc.CardBody([
                html.Div(id="results-table-container")
            ])
        ], className="shadow-sm mb-4"),

        # 图表区域（固定布局,由update_layout_based_on_data回调动态调整）
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📈 Melting Curves"),
                    dbc.CardBody([
                        dcc.Graph(id='melting-curves-plot', style={'height': '400px'})
                    ])
                ], className="shadow-sm")
            ], id='melting-curves-column', md=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Tm Distribution"),
                    dbc.CardBody([
                        dcc.Graph(id='tm-distribution-plot', style={'height': '400px'})
                    ])
                ], className="shadow-sm")
            ], id='tm-dist-column', md=6),
        ]),

    ], className="p-3")


def _create_thermo_analysis_content(results_data) -> html.Div:
    """创建热力学分析内容 - Split-View架构: 表格区(上) + 图表区(下)"""
    
    has_data = results_data and results_data.get('results')
    has_concentration = has_data and any(r.get('concentration') for r in results_data['results'])
    
    if not has_concentration:
        return html.Div([
            dbc.Alert([
                html.I(className="fas fa-flask me-2"),
                "Thermodynamic analysis requires concentration series data. ",
                "Please ensure filenames contain concentration info (e.g., 1uM, 500nM, etc.)"
            ], color="warning", className="mb-4"),
            
            # 占位图表
            dbc.Card([
                dbc.CardHeader("📈 Van't Hoff Analysis"),
                dbc.CardBody([
                    dcc.Graph(
                        figure=_create_empty_figure("Concentration data required for Van't Hoff analysis"),
                        style={'height': '450px'}
                    )
                ])
            ], className="shadow-sm"),
        ], className="p-3")
    
    # 有浓度数据时显示完整界面 - Split-View架构
    return html.Div([
        # ==================== TABLE AREA (Top ~35vh) ====================
        html.Div([
            # 分析参数 (紧凑行)
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Protein Conc (nM)", className="small mb-1"),
                            dbc.Input(
                                id="protein-conc-input",
                                type="number",
                                value=100,
                                min=0.1,
                                step=0.1,
                                size="sm"
                            )
                        ], md=2),
                        dbc.Col([
                            dbc.Label("Temperature Slices (°C)", className="small mb-1"),
                            dcc.RangeSlider(
                                id="vh-temp-slice-range",
                                min=20,
                                max=100,
                                step=0.5,
                                value=[30, 80],
                                tooltip={"placement": "bottom", "always_visible": False}
                            ),
                            html.Div(id="vh-temp-range-label", className="text-muted small")
                        ], md=5),
                        dbc.Col([
                            dbc.Label("Method", className="small mb-1"),
                            dbc.RadioItems(
                                id="vh-method-selector",
                                options=[
                                    {"label": "Auto-optimize", "value": "optimize"},
                                    {"label": "All points", "value": "all"},
                                ],
                                value="optimize",
                                inline=True,
                                className="small"
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="fas fa-play me-1"), "Run Van't Hoff"],
                                id="run-vanthoff-btn",
                                color="primary",
                                size="sm",
                                className="mt-4"
                            )
                        ], md=2),
                    ], className="align-items-center"),
                ], className="py-2")
            ], className="shadow-sm mb-2"),
            
            # 数据表格区 - 带Tabs (Data Selection | Isothermal EC50/KD)
            dbc.Card([
                dbc.CardBody([
                    dbc.Tabs([
                        # Tab 1: Data Selection
                        dbc.Tab(
                            label="📋 Data Selection",
                            tab_id="thermo-data-selection",
                            children=html.Div([
                                html.Div([
                                    html.I(className="fas fa-check-square me-2"),
                                    html.Span(id="vh-selection-hint", className="text-muted small")
                                ], className="mb-2"),
                                dash_table.DataTable(
                                    id='vh-selection-table',
                                    columns=[
                                        {"name": "Sample", "id": "name"},
                                        {"name": "Conc (nM)", "id": "conc_nM"},
                                        {"name": "Tm (°C)", "id": "tm"},
                                        {"name": "R²", "id": "r2"},
                                        {"name": "Method", "id": "method"},
                                        {"name": "Status", "id": "quality"},
                                    ],
                                    data=[],
                                    row_selectable="multi",
                                    selected_rows=[],
                                    page_size=30,
                                    style_table={"overflowX": "auto", "maxHeight": "15vh", "overflowY": "auto"},
                                    style_cell={"padding": "4px", "fontSize": 11},
                                    style_header={"fontWeight": "bold", "fontSize": 11},
                                )
                            ], className="p-1")
                        ),
                        # Tab 2: Isothermal EC50/KD Table
                        dbc.Tab(
                            label="📊 Isothermal EC50/KD",
                            tab_id="thermo-isothermal-tab",
                            children=html.Div([
                                dash_table.DataTable(
                                    id='isothermal-ec50-table',
                                    columns=[
                                        {"name": "Temp (°C)", "id": "temp"},
                                        {"name": "EC50", "id": "ec50"},
                                        {"name": "KD", "id": "kd"},
                                        {"name": "Dynamic Range", "id": "dr"},
                                        {"name": "4PL R²", "id": "r2"},
                                        {"name": "Points", "id": "n_points"},
                                    ],
                                    data=[],
                                    page_size=30,
                                    style_table={"overflowX": "auto", "maxHeight": "15vh", "overflowY": "auto"},
                                    style_cell={"padding": "4px", "fontSize": 11},
                                    style_header={"fontWeight": "bold", "fontSize": 11},
                                )
                            ], className="p-1")
                        ),
                    ], id="thermo-table-tabs", active_tab="thermo-data-selection")
                ], className="p-2")
            ], className="shadow-sm mb-2"),
            
            # 热力学参数卡片 (紧凑行)
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div("ΔH", className="text-muted small"),
                            html.Div(id="vh-delta-h", children="-- kJ/mol", className="text-primary fw-bold")
                        ], className="py-1 px-2 text-center")
                    ], className="shadow-sm h-100")
                ], xs=6, md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div("ΔS", className="text-muted small"),
                            html.Div(id="vh-delta-s", children="-- J/mol·K", className="text-success fw-bold")
                        ], className="py-1 px-2 text-center")
                    ], className="shadow-sm h-100")
                ], xs=6, md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div("R²", className="text-muted small"),
                            html.Div(id="vh-r2", children="--", className="text-warning fw-bold")
                        ], className="py-1 px-2 text-center")
                    ], className="shadow-sm h-100")
                ], xs=6, md=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div("KD (298K)", className="text-muted small"),
                            html.Div(id="vh-kd-298", children="-- nM", className="text-info fw-bold")
                        ], className="py-1 px-2 text-center")
                    ], className="shadow-sm h-100")
                ], xs=6, md=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div("KD (310K)", className="text-muted small"),
                            html.Div(id="vh-kd-310", children="-- nM", className="text-info fw-bold")
                        ], className="py-1 px-2 text-center")
                    ], className="shadow-sm h-100")
                ], xs=6, md=3),
            ], className="g-2 mb-2"),
        ], style={"marginBottom": "0.5rem"}),

        # ==================== PLOT AREA (Bottom ~55vh) ====================
        html.Div([
            dbc.Card([
                dbc.CardBody([
                    dbc.Tabs([
                        # Tab 1: Van't Hoff Plot
                        dbc.Tab(
                            label="📈 Van't Hoff Plot",
                            tab_id="thermo-vanthoff",
                            children=html.Div([
                                dcc.Graph(id='vanthoff-plot', style={'height': '48vh'}),
                                html.Div(id="thermo-qc-status-container", className="mt-2")
                            ])
                        ),
                        # Tab 2: Overlay Plot
                        dbc.Tab(
                            label="📊 AUC Overlay",
                            tab_id="thermo-overlay",
                            children=html.Div([
                                dcc.Graph(id='vh-overlay-plot', style={'height': '50vh'})
                            ])
                        ),
                    ], id="thermo-plot-tabs", active_tab="thermo-vanthoff")
                ], className="p-2")
            ], className="shadow-sm"),
        ]),
        
    ], className="p-3")


def _create_dose_response_content(results_data) -> html.Div:
    """创建剂量响应内容 - Split-View架构: 表格区(上) + 图表区(下)"""
    
    return html.Div([
        # ==================== TABLE AREA (Top ~35vh) ====================
        html.Div([
            # 表格区 - 带Tabs (Data Selection | Results & QC)
            dbc.Card([
                dbc.CardBody([
                    dbc.Tabs([
                        # Tab 1: Data Selection
                        dbc.Tab(
                            label="📋 Data Selection",
                            tab_id="dr-data-selection",
                            children=html.Div([
                                html.Div([
                                    html.I(className="fas fa-check-square me-2"),
                                    html.Span(id="dr-selection-hint", className="text-muted small"),
                                    dbc.Button(
                                        [html.I(className="fas fa-calculator me-1"), "Calculate EC50"],
                                        id="dr-run-btn",
                                        color="primary",
                                        size="sm",
                                        className="float-end"
                                    )
                                ], className="mb-2"),
                                dash_table.DataTable(
                                    id='dr-selection-table',
                                    columns=[
                                        {"name": "Sample", "id": "name"},
                                        {"name": "Conc (nM)", "id": "conc_nM"},
                                        {"name": "Tm (°C)", "id": "tm"},
                                        {"name": "R²", "id": "r2"},
                                        {"name": "Method", "id": "method"},
                                        {"name": "Status", "id": "quality"},
                                    ],
                                    data=[],
                                    row_selectable="multi",
                                    selected_rows=[],
                                    page_size=30,
                                    style_table={"overflowX": "auto", "maxHeight": "22vh", "overflowY": "auto"},
                                    style_cell={"padding": "4px", "fontSize": 11},
                                    style_header={"fontWeight": "bold", "fontSize": 11},
                                )
                            ], className="p-1")
                        ),
                        # Tab 2: Results & QC
                        dbc.Tab(
                            label="📊 Results & QC",
                            tab_id="dr-results-qc",
                            children=html.Div([
                                html.Div(id="dr-ec50-results", children=[
                                    html.P("Run EC50 analysis to see results...", 
                                           className="text-muted text-center py-4")
                                ])
                            ], className="p-1", style={"maxHeight": "22vh", "overflowY": "auto"})
                        ),
                    ], id="dr-table-tabs", active_tab="dr-data-selection")
                ], className="p-2")
            ], className="shadow-sm mb-2"),
        ], style={"marginBottom": "0.5rem"}),

        # ==================== PLOT AREA (Bottom ~60vh) ====================
        html.Div([
            dbc.Card([
                dbc.CardBody([
                    dbc.Tabs([
                        # Tab 1: Dose-Response Curve
                        dbc.Tab(
                            label="📈 Dose-Response Curve",
                            tab_id="dr-curve",
                            children=html.Div([
                                dcc.Graph(
                                    id='dose-response-plot',
                                    figure=_create_empty_figure("Run analysis to see dose-response curve"),
                                    style={'height': '55vh'}
                                )
                            ])
                        ),
                        # Tab 2: SFQ/SFE Analysis
                        dbc.Tab(
                            label="🔬 SFQ/SFE Analysis",
                            tab_id="dr-sfq",
                            children=html.Div([
                                html.Div(id="sfq-analysis-content", children=[
                                    dbc.Alert([
                                        html.I(className="fas fa-info-circle me-2"),
                                        "SFQ analysis detects systematic changes in native-state fluorescence ",
                                        "as a function of ligand concentration. Results appear here after running EC50 analysis."
                                    ], color="info", className="mt-3")
                                ])
                            ])
                        ),
                    ], id="dr-plot-tabs", active_tab="dr-curve")
                ], className="p-2")
            ], className="shadow-sm"),
        ]),
        
        # Hidden elements for SFQ collapse (keep for callback compatibility)
        html.Div(id="sfq-card-header", style={"display": "none"}),
        html.Div(id="sfq-collapse", style={"display": "none"}),
        
    ], className="p-3")


def _create_empty_figure(message: str) -> go.Figure:
    """创建空图表占位"""
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

