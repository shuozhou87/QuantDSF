#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export Callbacks
=================
导出相关回调 - Complete export package generation
"""

import base64
from dash import Dash, Input, Output, State, dcc, callback_context
from typing import Optional, Dict, Any
import plotly.graph_objects as go

from core.io.exporters import create_complete_export_package


def register_export_callbacks(app: Dash) -> None:
    """注册导出相关回调"""

    @app.callback(
        Output('download-export-package', 'data'),
        Input('export-btn', 'n_clicks'),
        State('analysis-results-store', 'data'),
        State('dose-response-store', 'data'),
        State('thermodynamics-store', 'data'),
        State('method-selector', 'value'),
        State('channel-selector', 'value'),
        State('units-selector', 'value'),
        State('slice-step-input', 'value'),
        State('min-dr-input', 'value'),
        State('min-4pl-r2-input', 'value'),
        State('vh-optimize-checkbox', 'value'),
        State('vh-min-points-input', 'value'),
        # Figure states - we'll get figures from the UI components
        State('melting-curves-plot', 'figure'),
        State('tm-distribution-plot', 'figure'),
        State('dose-response-plot', 'figure'),
        State('vanthoff-plot', 'figure'),
        State('vh-overlay-plot', 'figure'),
        State('isothermal-panels-plot', 'figure'),
        prevent_initial_call=True
    )
    def export_complete_package(
        n_clicks,
        basic_data,
        dose_response_data,
        thermodynamics_data,
        method,
        channel,
        units,
        slice_step,
        min_dr,
        min_4pl_r2,
        vh_optimize,
        vh_min_points,
        melting_curves_fig,
        tm_dist_fig,
        dose_response_fig,
        vanthoff_fig,
        vh_overlay_fig,
        isothermal_panels_fig
    ):
        """
        Export complete analysis package (Excel + PNG figures) as ZIP.

        Collects all analysis results and figures from the UI, packages them
        into a timestamped ZIP file.

        Returns:
            dcc.send_bytes: ZIP package download
        """
        if not n_clicks:
            return None

        # Build settings data dictionary
        settings_data = {
            'basic_analysis': {
                'method': method,
                'channel': channel
            },
            'dose_response': {
                'fitting_method': '4-Parameter Logistic'
            },
            'thermodynamics': {
                'units': units,
                'slice_step': slice_step,
                'min_dr': min_dr,
                'min_4pl_r2': min_4pl_r2,
                'vh_optimize': vh_optimize,
                'vh_min_points': vh_min_points
            }
        }

        # Collect all figures (convert from dict to Figure objects)
        figures = {}
        if melting_curves_fig:
            figures['melting-curves-plot'] = go.Figure(melting_curves_fig)
        if tm_dist_fig:
            figures['tm-distribution-plot'] = go.Figure(tm_dist_fig)
        if dose_response_fig:
            figures['dose-response-plot'] = go.Figure(dose_response_fig)
        if vanthoff_fig:
            figures['vanthoff-plot'] = go.Figure(vanthoff_fig)
        if vh_overlay_fig:
            figures['vh-overlay-plot'] = go.Figure(vh_overlay_fig)
        if isothermal_panels_fig:
            figures['isothermal-panels-plot'] = go.Figure(isothermal_panels_fig)

        # Create export package
        try:
            zip_bytes, zip_filename = create_complete_export_package(
                basic_data=basic_data,
                dose_response_data=dose_response_data,
                thermodynamics_data=thermodynamics_data,
                settings_data=settings_data,
                figures=figures
            )

            # Return download
            return dcc.send_bytes(zip_bytes, zip_filename)

        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"Export error: {str(e)}")
            return None


