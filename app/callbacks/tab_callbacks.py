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
        Output('tm-dist-column', 'style'),
        Output('melting-curves-column', 'md'),
        Output('melting-curves-plot', 'style'),
        Input('analysis-results-store', 'data'),
    )
    def update_layout_based_on_data(results_data):
        """根据数据类型动态调整布局"""
        if not results_data or not results_data.get('results'):
            # 无数据:默认布局
            return {}, 6, {'height': '400px'}

        results = results_data['results']
        valid_conc_count = sum(1 for r in results if r.get('concentration') is not None)
        is_dose_response = valid_conc_count >= 3

        if is_dose_response:
            # 浓度梯度:隐藏Tm Distribution,Melting Curves全宽
            return {'display': 'none'}, 12, {'height': '500px'}
        else:
            # 普通样品:显示两个图
            return {}, 6, {'height': '400px'}
    
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
    """创建热力学分析内容"""
    
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
    
    # 有浓度数据时显示完整界面
    return html.Div([
        dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "Select data points for Van't Hoff analysis and enter protein concentration to run"
        ], color="info", className="mb-4"),
        
        # 蛋白浓度输入 / 温度窗口 / 方法
        dbc.Card([
            dbc.CardHeader("⚙️ Analysis Parameters"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Protein Concentration (nM)"),
                        dbc.Input(
                            id="protein-conc-input",
                            type="number",
                            value=100,
                            min=0.1,
                            step=0.1
                        )
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Temperature slices (°C)"),
                        dcc.RangeSlider(
                            id="vh-temp-slice-range",
                            min=20,
                            max=100,
                            step=0.5,
                            value=[30, 80],
                            tooltip={"placement": "bottom", "always_visible": False}
                        ),
                        html.Div(id="vh-temp-range-label", className="text-muted small mt-1")
                    ], md=5),
                    dbc.Col([
                        dbc.Label("Method"),
                        dbc.RadioItems(
                            id="vh-method-selector",
                            options=[
                                {"label": "Auto-optimize low-T subset", "value": "optimize"},
                                {"label": "Use all points", "value": "all"},
                            ],
                            value="optimize",
                            inline=True
                        )
                    ], md=3),
                ]),
                html.Hr(),
                dbc.Button(
                    [html.I(className="fas fa-play me-2"), "Run Van't Hoff Analysis"],
                    id="run-vanthoff-btn",
                    color="primary"
                )
            ])
        ], className="shadow-sm mb-4"),

        # 数据点选择
        dbc.Card([
            dbc.CardHeader("🔎 Data Selection for Van't Hoff"),
            dbc.CardBody([
                html.Div(id="vh-selection-hint", className="text-muted small mb-2"),
                dash_table.DataTable(
                    id='vh-selection-table',
                    columns=[
                        {"name": "Sample", "id": "name"},
                        {"name": "Concentration (nM)", "id": "conc_nM"},
                        {"name": "Tm (°C)", "id": "tm"},
                        {"name": "R²", "id": "r2"},
                        {"name": "Method", "id": "method"},
                        {"name": "Status", "id": "quality"},
                    ],
                    data=[],
                    row_selectable="multi",
                    selected_rows=[],
                    page_size=20,
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "fontSize": 12},
                    style_header={"fontWeight": "bold"},
                )
            ])
        ], className="shadow-sm mb-4"),
        
        # 热力学参数卡片
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("ΔH", className="text-muted mb-1"),
                        html.H3(id="vh-delta-h", children="-- kJ/mol", className="text-primary mb-0")
                    ])
                ], className="shadow-sm text-center")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("ΔS", className="text-muted mb-1"),
                        html.H3(id="vh-delta-s", children="-- J/mol·K", className="text-success mb-0")
                    ])
                ], className="shadow-sm text-center")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("KD (298K)", className="text-muted mb-1"),
                        html.H3(id="vh-kd-298", children="-- nM", className="text-info mb-0")
                    ])
                ], className="shadow-sm text-center")
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("KD (310K / 37°C)", className="text-muted mb-1"),
                        html.H3(id="vh-kd-310", children="-- nM", className="text-info mb-0")
                    ])
                ], className="shadow-sm text-center")
            ], md=3),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("R²", className="text-muted mb-1"),
                        html.H3(id="vh-r2", children="--", className="text-warning mb-0")
                    ])
                ], className="shadow-sm text-center")
            ], md=3),
        ], className="mb-4"),
        
        # Van't Hoff 图
        dbc.Card([
            dbc.CardHeader("📈 Van't Hoff Plot"),
            dbc.CardBody([
                dcc.Graph(id='vanthoff-plot', style={'height': '450px'}),
                # QC 状态卡片
                html.Div(id="thermo-qc-status-container", className="mt-3")
            ])
        ], className="shadow-sm mb-4"),

        # 归一化曲线叠加
        dbc.Card([
            dbc.CardHeader("📊 Normalized AUC Overlay (temperature slices)"),
            dbc.CardBody([
                dcc.Graph(id='vh-overlay-plot', style={'height': '450px'})
            ])
        ], className="shadow-sm mb-4"),

        # 等温 EC50 / KD 表
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                "Isothermal EC50 / KD Table"
            ]),
            dbc.CardBody([
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
                    page_size=25,
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "fontSize": 12},
                    style_header={"fontWeight": "bold"},
                )
            ])
        ], className="shadow-sm"),
        
    ], className="p-3")


def _create_dose_response_content(results_data) -> html.Div:
    """创建剂量响应内容"""
    print("[DEBUG] _create_dose_response_content called")

    return html.Div([
        dbc.Alert([
            html.I(className="fas fa-chart-line me-2"),
            "Dose-Response EC50 Analysis - Fit Tm vs Concentration with 4PL curve"
        ], color="info", className="mb-4"),

        # Data selection table
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-check-square me-2"),
                "1️⃣ Select Data Points for EC50 Fitting"
            ]),
            dbc.CardBody([
                dbc.Alert(
                    "💡 Select samples to include in EC50 fitting. Need at least 3 points with valid concentration and Tm.",
                    color="info",
                    className="py-2 mb-3"
                ),
                html.Div(id="dr-selection-hint", className="text-muted small mb-2"),
                dash_table.DataTable(
                    id='dr-selection-table',
                    columns=[
                        {"name": "Sample", "id": "name"},
                        {"name": "Concentration (nM)", "id": "conc_nM"},
                        {"name": "Tm (°C)", "id": "tm"},
                        {"name": "R²", "id": "r2"},
                        {"name": "Method", "id": "method"},
                        {"name": "Status", "id": "quality"},
                    ],
                    data=[],
                    row_selectable="multi",
                    selected_rows=[],
                    page_size=20,
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "fontSize": 12},
                    style_header={"fontWeight": "bold"},
                )
            ])
        ], className="shadow-sm mb-4"),

        # Run button
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-play me-2"),
                "2️⃣ Run EC50 Analysis"
            ]),
            dbc.CardBody([
                dbc.Button(
                    [html.I(className="fas fa-calculator me-2"), "Calculate EC50"],
                    id="dr-run-btn",
                    color="primary",
                    size="lg",
                    className="w-100"
                )
            ])
        ], className="shadow-sm mb-4"),

        # Results display
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-chart-bar me-2"),
                "3️⃣ EC50 Results"
            ]),
            dbc.CardBody([
                html.Div(id="dr-ec50-results", children=[
                    html.P("Click 'Calculate EC50' to see results...", className="text-muted text-center py-3")
                ])
            ])
        ], className="shadow-sm mb-4"),

        # Dose-response plot
        dbc.Card([
            dbc.CardHeader("📈 Dose-Response Curve"),
            dbc.CardBody([
                dcc.Graph(
                    id='dose-response-plot',
                    figure=_create_empty_figure("Run analysis to see dose-response curve"),
                    style={'height': '500px'}
                )
            ])
        ], className="shadow-sm"),

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

