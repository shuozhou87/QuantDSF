#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Navigation Bar Component
=========================
顶部导航栏组件
"""

from dash import html
import dash_bootstrap_components as dbc


GITHUB_URL = "https://github.com/shuozhou87/QuantDSF"


def create_navbar() -> dbc.Navbar:
    """创建顶部导航栏"""
    return dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.I(className="fas fa-flask fa-2x text-white")),
                    dbc.Col([
                        html.Span("QuantDSF", className="fw-bold text-white", style={"fontSize": "2.5rem", "lineHeight": "1"}),
                        html.Span("nanoDSF Analysis Platform", className="text-white-50 ms-3 text-nowrap", style={"fontSize": "1.1rem", "whiteSpace": "nowrap"})
                    ], className="d-flex align-items-baseline ms-3 text-nowrap"),
                ], align="center", className="g-0"),
                href="/",
                style={"textDecoration": "none"},
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-github me-1"),
                        "GitHub"
                    ], href=GITHUB_URL, target="_blank", external_link=True)),
                ], className="ms-auto", navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ], fluid=True),
        color="dark",
        dark=True,
        className="mb-4 shadow"
    )
