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

from core.io.exporters import create_complete_export_package, create_pdf_export


def register_export_callbacks(app: Dash) -> None:
    """注册导出相关回调"""

    @app.callback(
        Output('download-export-package', 'data'),
        Input('export-btn', 'n_clicks'),
        State('analysis-results-store', 'data'),
        State('dose-response-store', 'data'),
        State('thermodynamics-store', 'data'),
        State('melting-curves-plot', 'figure'),
        State('tm-distribution-plot', 'figure'),
        State('dose-response-plot', 'figure'),
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
        melting_curves_fig,
        tm_dist_fig,
        dose_response_fig,
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
        Export complete analysis package as comprehensive PDF report.

        Collects all analysis results and figures from the UI and packages them
        into a professional PDF report with all visualizations and QC details.

        Returns:
            dcc.send_bytes: PDF report download
        """
        print(f"[EXPORT] Callback triggered: n_clicks={n_clicks}")

        if not n_clicks:
            print("[EXPORT] No clicks yet, returning None")
            return None

        print(f"[EXPORT] Starting PDF export process...")

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

        # Collect figures from UI components
        figures = {}

        # Basic analysis figures
        if melting_curves_fig:
            try:
                figures['melting-curves-plot'] = go.Figure(melting_curves_fig)
            except Exception as e:
                print(f"Warning: Could not load melting curves figure: {e}")

        if tm_dist_fig:
            try:
                figures['tm-distribution-plot'] = go.Figure(tm_dist_fig)
            except Exception as e:
                print(f"Warning: Could not load Tm distribution figure: {e}")

        # Dose-response figures
        if dose_response_fig:
            try:
                figures['dose-response-plot'] = go.Figure(dose_response_fig)
            except Exception as e:
                print(f"Warning: Could not load dose-response figure: {e}")

        # SFQ figure (from dose_response_data store)
        if dose_response_data and dose_response_data.get('sfq_figure'):
            try:
                figures['sfq-plot'] = go.Figure(dose_response_data['sfq_figure'])
            except Exception as e:
                print(f"Warning: Could not load SFQ figure: {e}")

        # Thermodynamics figures (from thermodynamics_data store)
        if thermodynamics_data:
            # Van't Hoff plot
            if thermodynamics_data.get('figure'):
                try:
                    figures['vanthoff-plot'] = go.Figure(thermodynamics_data['figure'])
                except Exception as e:
                    print(f"Warning: Could not load Van't Hoff figure: {e}")

            # Overlay and isothermal plots (if stored)
            if thermodynamics_data.get('overlay_figure'):
                try:
                    figures['vh-overlay-plot'] = go.Figure(thermodynamics_data['overlay_figure'])
                except Exception as e:
                    print(f"Warning: Could not load overlay figure: {e}")

            if thermodynamics_data.get('isothermal_figure'):
                try:
                    figures['isothermal-panels-plot'] = go.Figure(thermodynamics_data['isothermal_figure'])
                except Exception as e:
                    print(f"Warning: Could not load isothermal figure: {e}")

        # Generate PDF report
        try:
            print("[EXPORT] Generating PDF report...")
            pdf_bytes, pdf_filename = create_pdf_export(
                basic_data=basic_data,
                dose_response_data=dose_response_data,
                thermodynamics_data=thermodynamics_data,
                settings_data=settings_data,
                figures=figures
            )
            print(f"[EXPORT] PDF generated: {pdf_filename} ({len(pdf_bytes)} bytes)")
            return dcc.send_bytes(pdf_bytes, pdf_filename)

        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"[EXPORT] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


