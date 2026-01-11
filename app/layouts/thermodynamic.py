#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thermodynamic Analysis Layout
==============================
热力学分析（Van't Hoff）页面布局
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from dash import dash_table


def create_thermodynamic_layout() -> html.Div:
    """创建热力学分析页面布局"""
    return html.Div([
        # 前置检查提示
        dbc.Alert(
            id="thermo-prerequisite-alert",
            color="warning",
            is_open=False,
            className="mb-3"
        ),
        
        # Step 1: 数据点选择
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-check-square me-2"),
                "1️⃣ Select Data Points for Analysis"
            ]),
            dbc.CardBody([
                dbc.Alert(
                    "💡 Deselect poor-quality curves to improve Van't Hoff regression accuracy.",
                    color="info",
                    className="py-2"
                ),
                html.Div(id="curve-selection-table-container")
            ])
        ], className="shadow-sm mb-4"),
        
        # Step 2: 曲线叠加可视化
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-chart-line me-2"),
                "2️⃣ Overlay Curves - Data Quality Check"
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Raw Normalized Data", className="fw-bold text-center d-block mb-2"),
                        dcc.Graph(id='overlay-raw-plot', style={'height': '350px'})
                    ], md=6),
                    dbc.Col([
                        html.Label("4PL Fitted Curves", className="fw-bold text-center d-block mb-2"),
                        dcc.Graph(id='overlay-4pl-plot', style={'height': '350px'})
                    ], md=6),
                ])
            ])
        ], className="shadow-sm mb-4"),
        
        # Step 3: EC50(T) 数据点选择
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-filter me-2"),
                "3️⃣ EC50(T) Data Selection for Van't Hoff"
            ]),
            dbc.CardBody([
                # 蛋白浓度输入与温度切片
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Protein Concentration (M, supports nM/µM input)"),
                        dbc.Input(
                            id="protein-conc-input",
                            type="text",
                            placeholder="e.g., 1e-6 for 1 µM"
                        ),
                        dbc.FormText("Leave empty to use EC50 as KD approximation")
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Temperature slices (°C)"),
                        dcc.RangeSlider(
                            id="vh-temp-slice-range",
                            min=20,
                            max=100,
                            step=0.5,
                            value=[30, 80],
                            marks={},
                            tooltip={"placement": "bottom", "always_visible": False}
                        ),
                        html.Div(id="vh-temp-range-label", className="text-muted small mt-1")
                    ], md=8),
                ], className="mb-3"),
                
                html.Div(id="ec50-selection-table-container")
            ])
        ], className="shadow-sm mb-4"),
        
        # Step 4: Van't Hoff 结果
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-chart-area me-2"),
                "4️⃣ Van't Hoff Results"
            ]),
            dbc.CardBody([
                # 结果指标 - 第一行：ΔH, ΔS, R²
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("ΔH", className="text-muted mb-1"),
                                html.H3(id="vh-delta-h", children="-- kJ/mol", className="text-primary mb-0")
                            ])
                        ], className="shadow-sm text-center")
                    ], md=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("ΔS", className="text-muted mb-1"),
                                html.H3(id="vh-delta-s", children="-- J/mol·K", className="text-success mb-0")
                            ])
                        ], className="shadow-sm text-center")
                    ], md=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("R²", className="text-muted mb-1"),
                                html.H3(id="vh-r2", children="--", className="text-secondary mb-0")
                            ])
                        ], className="shadow-sm text-center")
                    ], md=4),
                ], className="mb-2"),

                # 结果指标 - 第二行：KD值
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("KD (298K / 25°C)", className="text-muted mb-1"),
                                html.H3(id="vh-kd-298", children="-- nM", className="text-info mb-0")
                            ])
                        ], className="shadow-sm text-center")
                    ], md=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("KD (310K / 37°C)", className="text-muted mb-1"),
                                html.H3(id="vh-kd-310", children="-- nM", className="text-info mb-0")
                            ])
                        ], className="shadow-sm text-center")
                    ], md=6),
                ], className="mb-3", id="vanthoff-metrics-row"),
                
                # Van't Hoff 图
                dcc.Graph(id='vanthoff-plot', style={'height': '400px'}),

                # QC 状态卡片
                html.Div(id="thermo-qc-status-container", className="mt-3")
            ])
        ], className="shadow-sm mb-4"),
        
        # Step 5: 归一化曲线叠加
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-wave-square me-2"),
                "5️⃣ Normalized AUC Overlay (Temperature slices)"
            ]),
            dbc.CardBody([
                dcc.Graph(id='vh-overlay-plot', style={'height': '450px'})
            ])
        ], className="shadow-sm mb-4"),
        
        # Step 6: 等温剂量响应图
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-th me-2"),
                "6️⃣ Representative Isothermal Dose-Response Curves"
            ]),
            dbc.CardBody([
                dcc.Graph(id='isothermal-panels-plot', style={'height': '500px'})
            ])
        ], className="shadow-sm mb-4"),
        
        # 等温 EC50/KD 表格
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                "6️⃣ Isothermal EC50 / KD Table"
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
        ], className="shadow-sm mb-4"),
        
        # 导出
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-download me-2"),
                "7️⃣ Export Results"
            ]),
            dbc.CardBody([
                dbc.Button(
                    [html.I(className="fas fa-file-csv me-2"), "Download Van't Hoff Summary (CSV)"],
                    id="download-vanthoff-btn",
                    color="success",
                    className="me-2"
                ),
                dcc.Download(id="download-vanthoff-csv")
            ])
        ], className="shadow-sm"),
        
    ], className="p-3")

