#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dose-Response Analysis Layout
==============================
剂量响应分析页面布局
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_dose_response_layout() -> html.Div:
    """创建剂量响应分析页面布局"""
    return html.Div([
        # EC50 分析
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-chart-s me-2"),
                "EC50 Analysis"
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(
                            id='dose-response-plot',
                            style={'height': '500px'}
                        )
                    ], md=8),
                    dbc.Col([
                        html.H5("EC50 Results", className="mb-3"),
                        html.Div(id="ec50-results-container")
                    ], md=4),
                ])
            ])
        ], className="shadow-sm mb-4"),
        
        # ΔTm 筛选
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-filter me-2"),
                "ΔTm Screening"
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Select Control Sample"),
                        dcc.Dropdown(
                            id="control-sample-dropdown",
                            placeholder="Select control..."
                        )
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Significance Threshold (°C)"),
                        dbc.Input(
                            id="significance-threshold-input",
                            type="number",
                            value=3.0,
                            step=0.5
                        )
                    ], md=2),
                ], className="mb-3"),
                
                html.Div(id="delta-tm-table-container")
            ])
        ], className="shadow-sm"),
        
    ], className="p-3")


