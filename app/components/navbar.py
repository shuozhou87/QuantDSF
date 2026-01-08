#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Navigation Bar Component
=========================
顶部导航栏组件
"""

from dash import html
import dash_bootstrap_components as dbc


def create_navbar() -> dbc.Navbar:
    """创建顶部导航栏"""
    return dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.I(className="fas fa-flask fa-lg")),
                    dbc.Col(dbc.NavbarBrand("QuantDSF v2", className="ms-2 fw-bold")),
                ], align="center", className="g-0"),
                href="/",
                style={"textDecoration": "none"},
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-history me-1"),
                        "History"
                    ], href="#", id="nav-history")),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-book me-1"),
                        "Documentation"
                    ], href="#", id="nav-docs")),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-github me-1"),
                        "GitHub"
                    ], href="https://github.com", target="_blank")),
                ], className="ms-auto", navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ], fluid=True),
        color="dark",
        dark=True,
        className="mb-4 shadow"
    )


