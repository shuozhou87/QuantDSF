#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dose-Response Analysis Callbacks
==================================
Callbacks for Tm vs Concentration EC50 analysis
"""

from dash import Dash, Input, Output, State, html, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
from core.analysis.dose_response_ec50 import fit_tm_ec50, hill4_tm
from core.qc import DoseResponseQualityController
from core.qc.config import QCSettings


def register_dose_response_callbacks(app: Dash) -> None:
    """Register dose-response analysis callbacks"""

    @app.callback(
        Output('dr-selection-table', 'data'),
        Output('dr-selection-table', 'selected_rows'),
        Output('dr-selection-hint', 'children'),
        Input('analysis-results-store', 'data'),
        Input('main-tabs', 'active_tab'),
        prevent_initial_call=False
    )
    def populate_dr_table(results_data, active_tab):
        """Populate dose-response data selection table"""
        # Only populate when on dose-response tab
        if active_tab != 'dose':
            return no_update, no_update, no_update

        # Check if we have analysis results
        if not results_data or not results_data.get('results'):
            return [], [], "No analysis data. Run Tm analysis first."

        results = results_data['results']
        rows = []
        auto_selected = []

        for idx, r in enumerate(results):
            tm = r.get('tm')
            r2 = r.get('r_squared')
            conc = r.get('concentration')
            conc_nM = conc * 1e9 if conc is not None else None

            rows.append({
                "name": r.get('name'),
                "conc_nM": f"{conc_nM:.2f}" if conc_nM is not None else "N/A",
                "tm": f"{tm:.1f}" if tm is not None else "N/A",
                "r2": f"{r2:.3f}" if r2 is not None else "N/A",
                "method": r.get('method', '').upper(),
                "quality": r.get('quality_flag', '')
            })

            # Auto-select high quality fits (R² ≥ 0.85) with valid concentration
            if r2 is not None and r2 >= 0.85 and conc is not None and np.isfinite(conc) and conc > 0:
                auto_selected.append(idx)

        hint = f"{len(rows)} total samples; auto-selected {len(auto_selected)} high-quality points (R² ≥ 0.85). Adjust selection as needed."

        return rows, auto_selected, hint

    @app.callback(
        Output('dr-ec50-results', 'children'),
        Output('dose-response-plot', 'figure'),
        Output('dose-response-store', 'data'),
        Input('dr-run-btn', 'n_clicks'),
        State('analysis-results-store', 'data'),
        State('dr-selection-table', 'selected_rows'),
        State('dr-selection-table', 'data'),
        prevent_initial_call=True
    )
    def run_dose_response_analysis(n_clicks, results_data, selected_rows, table_data):
        """Run dose-response EC50 analysis"""
        # Empty figure
        fig = go.Figure()
        fig.update_layout(template='plotly_white')

        if not results_data or not results_data.get('results'):
            fig.add_annotation(
                text="No analysis data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return html.Div([
                dbc.Alert("No data available for analysis.", color="warning")
            ]), fig, None

        if not selected_rows or len(selected_rows) < 3:
            fig.add_annotation(
                text="Select at least 3 data points to fit dose-response curve",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return html.Div([
                dbc.Alert("Please select at least 3 data points with valid concentrations for EC50 fitting.", color="warning")
            ]), fig, None

        # Extract selected data
        # selected_rows contains the row indices directly corresponding to the results array
        results = results_data['results']
        concentrations = []
        tm_values = []
        names = []

        for row_idx in selected_rows:
            if row_idx < len(results):
                r = results[row_idx]
                conc = r.get('concentration')
                tm = r.get('tm')

                if conc is not None and tm is not None and np.isfinite(conc) and np.isfinite(tm) and conc > 0:
                    concentrations.append(conc)
                    tm_values.append(tm)
                    names.append(r.get('name', f'Sample {row_idx}'))

        if len(concentrations) < 3:
            fig.add_annotation(
                text="Insufficient valid data points (need ≥3 with valid concentration and Tm)",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return html.Div([
                dbc.Alert("Insufficient valid data points. Need at least 3 points with valid concentration and Tm.", color="danger")
            ]), fig, None

        concentrations = np.array(concentrations)
        tm_values = np.array(tm_values)

        # Fit 4PL curve
        fit_result = fit_tm_ec50(concentrations, tm_values)

        if not fit_result['success']:
            fig.add_annotation(
                text="EC50 fitting failed - insufficient data or poor fit quality",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return html.Div([
                dbc.Alert("EC50 fitting failed. Check data quality and concentration range.", color="danger")
            ]), fig, None

        # Run QC evaluation for dose-response analysis
        bottom = fit_result['bottom']
        top = fit_result['top']
        ec50 = fit_result['ec50']

        # Calculate dynamic range and data coverage
        dynamic_range_degc = abs(top - bottom)  # Theoretical Tm shift range (°C)
        experimental_range = tm_values.max() - tm_values.min()  # Actual Tm range in data
        data_coverage_pct = (experimental_range / dynamic_range_degc) * 100.0 if dynamic_range_degc > 0 else 0.0

        # Prepare data for QC evaluation with correct field names
        dr_result_dict = {
            'r_squared': fit_result['r2'],  # QC expects 'r_squared', not 'r2'
            'n_points': len(concentrations),
            'bottom': bottom,
            'top': top,
            'hill_slope': fit_result['hill_slope'],
            'EC50': ec50,  # QC expects 'EC50', not 'ec50'
            'EC50_err': fit_result.get('ec50_se'),  # Standard error from fitting
            'concentrations': concentrations.tolist(),  # QC expects 'concentrations' array
            'responses': tm_values.tolist(),  # Pass actual response data for coverage calculation
        }

        qc_controller = DoseResponseQualityController(settings=QCSettings())
        qc_metrics = qc_controller.evaluate(dr_result_dict)

        # Note: QC results are computed but not currently displayed in Tab 3 UI
        # Could be added to the results display in future enhancement

        # Create dose-response plot
        # Data points
        fig.add_trace(go.Scatter(
            x=concentrations,
            y=tm_values,
            mode='markers',
            marker=dict(
                size=10,
                color='darkblue',
                line=dict(width=1, color='white')
            ),
            name='Data points',
            text=names,
            hovertemplate='%{text}<br>Concentration: %{x:.2e} M<br>Tm: %{y:.1f} °C<extra></extra>'
        ))

        # Fitted curve
        conc_min = concentrations.min()
        conc_max = concentrations.max()
        conc_fit = np.logspace(np.log10(conc_min / 10), np.log10(conc_max * 10), 200)
        tm_fit = hill4_tm(conc_fit, *fit_result['popt'])

        fig.add_trace(go.Scatter(
            x=conc_fit,
            y=tm_fit,
            mode='lines',
            line=dict(color='red', width=3),
            name=f"4PL Fit (R² = {fit_result['r2']:.3f})",
            hovertemplate='Concentration: %{x:.2e} M<br>Predicted Tm: %{y:.1f} °C<extra></extra>'
        ))

        # EC50 vertical line
        ec50 = fit_result['ec50']
        ec50_tm = hill4_tm(np.array([ec50]), *fit_result['popt'])[0]

        fig.add_trace(go.Scatter(
            x=[ec50, ec50],
            y=[tm_values.min() - 2, ec50_tm],
            mode='lines',
            line=dict(color='green', width=2, dash='dash'),
            name=f'EC50 = {ec50:.2e} M',
            showlegend=True,
            hovertemplate=f'EC50: {ec50:.2e} M<extra></extra>'
        ))

        fig.update_layout(
            xaxis_type='log',
            xaxis_title='Concentration (M)',
            yaxis_title='Tm (°C)',
            title='Dose-Response Curve: Tm vs Concentration',
            template='plotly_white',
            hovermode='closest',
            height=500
        )

        # Create results display
        ec50_str = f"{ec50:.2e} M"
        if ec50 >= 1e-6:
            ec50_str += f" ({ec50*1e6:.2f} µM)"
        elif ec50 >= 1e-9:
            ec50_str += f" ({ec50*1e9:.2f} nM)"

        ci_str = f"{fit_result['ec50_ci'][0]:.2e} - {fit_result['ec50_ci'][1]:.2e} M"

        # Format QC flag with color
        qc_flag = qc_metrics.flag
        if qc_flag == '✅':
            qc_color = 'success'
            qc_badge_color = 'success'
        elif qc_flag == '⚠️':
            qc_color = 'warning'
            qc_badge_color = 'warning'
        else:
            qc_color = 'danger'
            qc_badge_color = 'danger'

        results_display = html.Div([
            dbc.Alert("✅ EC50 Analysis Complete", color="success", className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("EC50", className="text-muted mb-1"),
                            html.H4(ec50_str, className="text-primary mb-0")
                        ])
                    ], className="shadow-sm text-center mb-2")
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("95% CI", className="text-muted mb-1"),
                            html.H6(ci_str, className="text-success mb-0", style={"fontSize": "14px"})
                        ])
                    ], className="shadow-sm text-center mb-2")
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("R²", className="text-muted mb-1"),
                            html.H4(f"{fit_result['r2']:.4f}", className="text-info mb-0")
                        ])
                    ], className="shadow-sm text-center mb-2")
                ], md=4),
            ]),

            html.Hr(),

            # QC Summary
            dbc.Alert([
                html.Div([
                    html.Span("Quality: ", className="fw-bold"),
                    dbc.Badge(qc_flag, color=qc_badge_color, className="me-2"),
                    html.Span(f"Score: {qc_metrics.score:.1f}/100", className="text-muted small")
                ]),
                html.Div([
                    html.Small(qc_metrics.message, className="text-muted")
                ], className="mt-1") if qc_metrics.message else None,
                html.Div([
                    html.Small(qc_metrics.tooltip, className="mt-2 d-block")
                ]) if qc_metrics.tooltip else None
            ], color=qc_color, className="mb-3"),

            html.H6("Fitting Parameters", className="mt-3 mb-2"),
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Parameter"),
                        html.Th("Value")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td("Bottom (Tm0)"),
                        html.Td(f"{fit_result['bottom']:.2f} °C")
                    ]),
                    html.Tr([
                        html.Td("Top (Tm∞)"),
                        html.Td(f"{fit_result['top']:.2f} °C")
                    ]),
                    html.Tr([
                        html.Td("Hill Slope"),
                        html.Td(f"{fit_result['hill_slope']:.3f}")
                    ]),
                    html.Tr([
                        html.Td("Data Points"),
                        html.Td(f"{len(concentrations)}")
                    ]),
                    html.Tr([
                        html.Td("Dynamic Range (Top-Bottom)"),
                        html.Td(f"{dynamic_range_degc:.2f} °C")
                    ]),
                    html.Tr([
                        html.Td("Data Coverage"),
                        html.Td(f"{data_coverage_pct:.1f}%")
                    ])
                ])
            ], bordered=True, hover=True, size='sm', className="mb-3")
        ])

        # Prepare data for storage
        dose_response_data = {
            'ec50': ec50,
            'ec50_ci': fit_result['ec50_ci'],
            'r2': fit_result['r2'],
            'hill_slope': fit_result['hill_slope'],
            'bottom': bottom,
            'top': top,
            'n_points': len(concentrations),
            'concentrations': concentrations.tolist(),
            'tm_values': tm_values.tolist(),
            'qc_flag': qc_metrics.flag,
            'qc_message': qc_metrics.message,
            'qc_score': qc_metrics.score,
            'qc_tooltip': qc_metrics.tooltip if hasattr(qc_metrics, 'tooltip') else None,
            # Store figure for export
            'figure': fig
        }

        return results_display, fig, dose_response_data
