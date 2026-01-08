#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QuantDSF Dash Application
==========================
Dash 应用层 - 用户界面

使用示例:
    from app import create_app
    app = create_app()
    app.run(debug=True, port=8050)
"""

import dash
from dash import Dash
import dash_bootstrap_components as dbc

from .layouts import create_main_layout
from .callbacks import register_all_callbacks
from .state import AppState


def create_app(debug: bool = False) -> Dash:
    """
    应用工厂函数
    
    Args:
        debug: 是否启用调试模式
    
    Returns:
        配置好的 Dash 应用实例
    """
    app = Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.FLATLY,
            dbc.icons.FONT_AWESOME
        ],
        suppress_callback_exceptions=True,
        title="QuantDSF v2 - nanoDSF Analysis Platform"
    )
    
    # 创建布局
    app.layout = create_main_layout()
    
    # 初始化全局状态
    app._state = AppState()
    
    # 注册回调
    register_all_callbacks(app)
    
    return app


__all__ = ['create_app', 'AppState']


