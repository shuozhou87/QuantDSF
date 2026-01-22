#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sidebar Component
==================
侧边栏组件 - 文件上传和分析设置
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_sidebar() -> dbc.Card:
    """创建侧边栏"""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-cogs me-2"),
            html.Strong("Analysis Settings")
        ], className="bg-primary text-white"),
        
        dbc.CardBody([
            # 文件上传区
            _create_file_upload_section(),
            
            html.Hr(),
            
            # 分析方法设置
            _create_method_settings(),
            
            html.Hr(),
            
            # 热力学分析参数（可折叠）
            dbc.Accordion([
                dbc.AccordionItem([
                    _create_thermodynamic_settings()
                ], title="🔬 Van't Hoff Parameters")
            ], start_collapsed=True, className="mb-3"),

            # Advanced Settings（独立折叠面板）
            dbc.Accordion([
                dbc.AccordionItem([
                    _create_advanced_settings()
                ], title="⚙️ Advanced Settings")
            ], start_collapsed=True, className="mb-3"),

            # 运行和导出按钮
            _create_action_buttons(),
        ])
    ], className="shadow-sm", style={'position': 'sticky', 'top': '20px'})


def _create_file_upload_section() -> html.Div:
    """文件上传区域"""
    return html.Div([
        html.Label("📁 Data Upload", className="fw-bold mb-2"),
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.I(className="fas fa-cloud-upload-alt fa-2x mb-2"),
                html.Br(),
                'Drag & Drop or ',
                html.A('Browse Files', className="text-primary")
            ]),
            style={
                'width': '100%',
                'height': '100px',
                'lineHeight': '25px',
                'borderWidth': '2px',
                'borderStyle': 'dashed',
                'borderRadius': '10px',
                'textAlign': 'center',
                'padding': '15px',
                'cursor': 'pointer'
            },
            multiple=True
        ),
        html.Div(id='upload-status', className="mt-2 text-muted small"),
        html.Div(id='loaded-files-list', className="mt-2"),
        
        # Test Data Button (for development/debugging)
        dbc.Button(
            [html.I(className="fas fa-flask me-1"), "Load Test Data"],
            id='load-test-data-btn',
            color="secondary",
            outline=True,
            size="sm",
            className="w-100 mt-2"
        ),
        dbc.Tooltip(
            "Load RPA+SSDNA_13406_DOSE.zip for automated testing",
            target="load-test-data-btn",
            placement="bottom"
        ),
    ], className="mb-4")



def _create_method_settings() -> html.Div:
    """分析方法设置"""
    return html.Div([
        # 方法选择
        html.Div([
            html.Label("🔬 Tm Calculation Method", className="fw-bold mb-2"),
            dbc.RadioItems(
                id='method-selector',
                options=[
                    {'label': ' AUC (Progress Curve)', 'value': 'auc'},
                    {'label': ' Two-State Boltzmann', 'value': 'boltzmann'},
                    {'label': ' First Derivative', 'value': 'derivative'},
                ],
                value='auc',
                className="mb-3"
            ),
        ], className="mb-3"),
        
        # 通道选择
        html.Div([
            html.Label("📊 Data Channel", className="fw-bold mb-2"),
            dbc.Select(
                id='channel-selector',
                options=[
                    {'label': '350/330 nm Ratio', 'value': 'ratio'},
                    {'label': '350 nm', 'value': '350'},
                    {'label': '330 nm', 'value': '330'},
                ],
                value='ratio',
            ),
        ], className="mb-3"),
    ])


def _create_thermodynamic_settings() -> html.Div:
    """热力学分析参数"""
    return html.Div([
        # 单位选择
        html.Div([
            html.Label("Thermodynamic Units", className="fw-bold mb-2"),
            dbc.RadioItems(
                id='units-selector',
                options=[
                    {'label': ' Calorie (kcal/mol)', 'value': 'calorie'},
                    {'label': ' Joule (kJ/mol)', 'value': 'joule'},
                ],
                value='calorie',
                inline=True
            ),
        ], className="mb-3"),

        # 等温拟合参数
        html.Label("Isothermal Fitting", className="fw-bold mb-2"),
        
        html.Div([
            dbc.Label("Temperature slice spacing (°C)", className="small"),
            dbc.Input(
                id="slice-step-input",
                type="number",
                value=0.5,
                min=0.1,
                max=2.0,
                step=0.1,
                size="sm"
            ),
        ], className="mb-2"),
        
        html.Div([
            dbc.Label("Min dynamic range (%)", className="small"),
            dbc.Input(
                id="min-dr-input",
                type="number",
                value=20,
                min=10,
                max=50,
                step=5,
                size="sm"
            ),
        ], className="mb-2"),
        
        html.Div([
            dbc.Label("Min 4PL R²", className="small"),
            dbc.Input(
                id="min-4pl-r2-input",
                type="number",
                value=0.95,
                min=0.8,
                max=0.99,
                step=0.01,
                size="sm"
            ),
        ], className="mb-3"),
        
        # Van't Hoff 参数
        html.Label("Van't Hoff Regression", className="fw-bold mb-2"),
        
        dbc.Checkbox(
            id="vh-optimize-checkbox",
            label="Auto-optimize low-T subset",
            value=True,
            className="mb-2"
        ),
        
        html.Div([
            dbc.Label("Min points", className="small"),
            dbc.Input(
                id="vh-min-points-input",
                type="number",
                value=5,
                min=3,
                max=15,
                step=1,
                size="sm"
            ),
        ], className="mb-2"),
        
        # ΔCp 选项
        dbc.Checkbox(
            id="enable-cp-checkbox",
            label="Enable ΔCp fitting (experimental)",
            value=False,
            className="mb-2"
        ),
    ])


def _create_advanced_settings() -> html.Div:
    """高级设置选项"""
    return html.Div([
        # Thermodynamic Analysis Method Selection
        html.Div([
            html.Label("Thermodynamic Analysis Method", className="fw-bold small mb-2"),
            dbc.RadioItems(
                id="thermodynamic-method-radio",
                options=[
                    {
                        'label': 'Isothermal Slicing (Van\'t Hoff) - Requires concentration series',
                        'value': 'isothermal'
                    },
                    {
                        'label': 'Single-Curve Method (Wright 2017) - Single sample per condition',
                        'value': 'single_curve'
                    }
                ],
                value='isothermal',  # 默认使用原有方法
                className="mb-2"
            ),
            html.Small([
                html.Strong("Isothermal Slicing: ", className="text-primary"),
                "Extracts thermodynamics from concentration-dependent data (≥5 concentrations). ",
                html.Br(),
                html.Strong("Single-Curve: ", className="text-success"),
                "Extracts thermodynamics from temperature-dependent unfolding of a single curve. ",
                "Based on Wright et al. 2017 J. Phys. Chem. Lett."
            ], className="text-muted small"),
        ], className="mb-3"),

        # First Derivative Smoothing
        html.Div([
            html.Label("First Derivative Method", className="fw-bold small mb-2"),
            dbc.Checkbox(
                id="fd-use-tsb-smoothing-checkbox",
                label="Use TSB model for smoothing (experimental)",
                value=False,
                className="mb-2"
            ),
            html.Small([
                "When enabled, uses TSB analytical derivative instead of Savitzky-Golay filter. ",
                html.Br(),
                html.Strong("⚠️ Warning: ", className="text-warning"),
                "Model-based smoothing may mask complex transitions (multi-state unfolding, aggregation). ",
                "Use with caution for exploratory analysis."
            ], className="text-muted small"),
        ]),
    ])


def _create_action_buttons() -> html.Div:
    """操作按钮"""
    return html.Div([
        dbc.Button(
            [html.I(className="fas fa-play me-2"), "Run Analysis"],
            id='run-analysis-btn',
            color="primary",
            className="w-100 mb-3"
        ),

        html.Hr(),
        html.H6("Export", className="text-muted mb-2"),

        dbc.Button(
            [html.I(className="fas fa-file-pdf me-2"), "Export PDF Report"],
            id='export-btn',
            color="success",
            outline=True,
            className="w-100"
        ),
    ])


