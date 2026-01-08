#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Callback Registration
======================
回调函数注册
"""

from dash import Dash


def register_all_callbacks(app: Dash) -> None:
    """
    注册所有回调函数

    Args:
        app: Dash 应用实例
    """
    from .file_callbacks import register_file_callbacks
    from .tab_callbacks import register_tab_callbacks
    from .analysis_callbacks import register_analysis_callbacks
    from .thermo_callbacks import register_thermo_callbacks
    from .dose_response_callbacks import register_dose_response_callbacks

    register_file_callbacks(app)
    register_tab_callbacks(app)
    register_analysis_callbacks(app)
    register_thermo_callbacks(app)
    register_dose_response_callbacks(app)


__all__ = ['register_all_callbacks']

