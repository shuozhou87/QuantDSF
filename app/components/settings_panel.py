#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Settings Panel Component
=========================
设置面板组件
"""

from dash import html
import dash_bootstrap_components as dbc


def create_settings_panel() -> dbc.Card:
    """创建设置面板"""
    return dbc.Card([
        dbc.CardHeader("⚙️ Analysis Settings"),
        dbc.CardBody([
            # 内容由回调动态生成
            html.Div(id="settings-content")
        ])
    ])


