#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File Upload Component
======================
文件上传组件
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def create_file_upload() -> html.Div:
    """创建文件上传组件"""
    return dcc.Upload(
        id='upload-data',
        children=html.Div([
            html.I(className="fas fa-cloud-upload-alt fa-3x mb-3 text-primary"),
            html.Br(),
            html.H5('Drag & Drop Files Here'),
            html.P([
                'or ',
                html.A('click to browse', className="text-primary fw-bold")
            ], className="text-muted"),
            html.Small("Supported: ZIP files from Prometheus NT.48 or Tycho NT.6", 
                      className="text-muted")
        ]),
        style={
            'width': '100%',
            'minHeight': '150px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '15px',
            'textAlign': 'center',
            'padding': '30px',
            'cursor': 'pointer',
            'backgroundColor': '#f8f9fa',
            'transition': 'all 0.3s ease'
        },
        multiple=True,
        className="file-upload-zone"
    )


def create_loaded_files_list(file_names: list) -> html.Div:
    """
    创建已加载文件列表
    
    Args:
        file_names: 文件名列表
    
    Returns:
        文件列表组件
    """
    if not file_names:
        return html.Div()
    
    items = []
    for i, name in enumerate(file_names):
        items.append(
            dbc.ListGroupItem([
                html.Span(name, className="me-2"),
                dbc.Button(
                    html.I(className="fas fa-times"),
                    id={'type': 'remove-file-btn', 'index': i},
                    color="danger",
                    size="sm",
                    outline=True,
                    className="float-end"
                )
            ], className="d-flex justify-content-between align-items-center py-2")
        )
    
    return dbc.ListGroup(items, flush=True, className="mt-2")


