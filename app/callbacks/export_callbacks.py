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
        vh_min_points
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

        # Collect figures from stored data (where available)
        figures = {}

        # Dose-Response figure
        if dose_response_data and 'figure' in dose_response_data:
            try:
                figures['dose-response-plot'] = go.Figure(dose_response_data['figure'])
            except:
                pass

        # Thermodynamics figure
        if thermodynamics_data and 'figure' in thermodynamics_data:
            try:
                figures['vanthoff-plot'] = go.Figure(thermodynamics_data['figure'])
            except:
                pass

        # Note: Basic analysis figures are not stored yet
        # TODO: Store basic analysis figures (melting-curves-plot, tm-distribution-plot) in analysis-results-store

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


