#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dose-Response Analysis Callbacks
==================================
Callbacks for Tm vs Concentration EC50 analysis
Includes Static Fluorescence Quenching/Enhancement (SFQ/SFE) analysis
"""

from dash import Dash, Input, Output, State, html, no_update, dash_table
import dash_bootstrap_components as dbc
from dash import dcc
import plotly.graph_objects as go
import numpy as np
from core.analysis.dose_response_ec50 import fit_tm_ec50, hill4_tm
from core.analysis.sfq_analysis import analyze_sfq_dataset, format_sfq_summary
from core.qc import DoseResponseQualityController
from core.qc.config import QCSettings


def _create_sfq_default_content():
    """Create default SFQ content when analysis not available"""
    return html.P([
        html.I(className="fas fa-info-circle me-2 text-muted"),
        "SFQ analysis detects systematic changes in native-state fluorescence ",
        "as a function of ligand concentration. Results appear here after running EC50 analysis."
    ], className="text-muted mb-0")


def _create_sfq_figure(sfq_result):
    """Create SFQ analysis figure (separate from UI)"""
    if sfq_result is None:
        return None

    cr = sfq_result.channel_result

    # Create the plot
    fig = go.Figure()

    # Data points
    fig.add_trace(go.Scatter(
        x=sfq_result.concentrations,
        y=sfq_result.cold_fluorescence,
        mode='markers',
        marker=dict(size=10, color='darkblue', line=dict(width=1, color='white')),
        name=f'F{sfq_result.channel_name} Cold',
        hovertemplate='Conc: %{x:.2e} M<br>F_cold: %{y:.0f}<extra></extra>'
    ))

    # Linear fit
    conc_fit = np.logspace(
        np.log10(min(sfq_result.concentrations)),
        np.log10(max(sfq_result.concentrations)),
        100
    )
    fig.add_trace(go.Scatter(
        x=conc_fit,
        y=sfq_result.linear_fit_y,
        mode='lines',
        line=dict(color='gray', width=2, dash='dash'),
        name=f'Non-specific (R²={cr.r2_linear:.3f})'
    ))

    # 4PL fit (if available)
    if sfq_result.fourpl_fit_y:
        fig.add_trace(go.Scatter(
            x=conc_fit,
            y=sfq_result.fourpl_fit_y,
            mode='lines',
            line=dict(color='red', width=3),
            name=f'4PL (R²={cr.r2_4pl:.3f})'
        ))

        # EC50 vertical line (if detected)
        if cr.ec50_app:
            fig.add_trace(go.Scatter(
                x=[cr.ec50_app, cr.ec50_app],
                y=[min(sfq_result.cold_fluorescence) * 0.95, max(sfq_result.cold_fluorescence) * 1.05],
                mode='lines',
                line=dict(color='green', width=2, dash='dot'),
                name=f'EC50_app = {cr.ec50_app_str}',
                hovertemplate=f'EC50_app = {cr.ec50_app_str}<extra></extra>'
            ))

    fig.update_layout(
        xaxis_type='log',
        xaxis_title='Concentration (M)',
        yaxis_title=f'Cold Fluorescence F{sfq_result.channel_name}',
        title=f'Static Fluorescence Analysis (F{sfq_result.channel_name})',
        template='plotly_white',
        height=400,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.8)"
        ),
        margin=dict(r=150)
    )

    return fig


def _create_sfq_results_ui(sfq_result, channel):
    """Create SFQ results UI components"""
    if sfq_result is None:
        if 'ratio' in channel.lower():
            return html.Div([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "SFQ analysis is not available for ratio channel. ",
                    "Please select 330nm or 350nm channel to enable this analysis."
                ], color="info", className="mb-0")
            ])
        return html.Div([
            dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                "Insufficient data for SFQ analysis (need at least 4 samples with valid concentrations)."
            ], color="warning", className="mb-0")
        ])

    cr = sfq_result.channel_result
    summary = format_sfq_summary(sfq_result)

    # Determine status color and icon
    if cr.status == 'Not detected':
        # Distinguish between non-specific binding (yellow) vs truly no signal (gray)
        if cr.notes and 'Non-specific model fits equally well' in cr.notes:
            # Non-specific binding detected - use yellow to indicate cautionary finding
            status_color = 'warning'
            status_icon = 'fas fa-exclamation-triangle'
        else:
            # Truly no signal or other failure - use gray
            status_color = 'secondary'
            status_icon = 'fas fa-minus-circle'
    elif cr.status == 'Detected':
        status_color = 'success'
        status_icon = 'fas fa-check-circle'
    else:  # Detected (caution)
        status_color = 'warning'
        status_icon = 'fas fa-exclamation-triangle'

    # Create figure using shared function
    fig = _create_sfq_figure(sfq_result)

    # Build metrics table
    metrics_rows = [
        html.Tr([html.Td("Status"), html.Td(dbc.Badge(cr.status, color=status_color))]),
        html.Tr([html.Td("Signal Change"), html.Td(f"{cr.span:.1f}%")]),
        html.Tr([html.Td("ΔAIC (non-specific - 4PL)"), html.Td(f"{cr.delta_aic:.1f}")]),
    ]

    # Show SI as the primary and only saturation metric
    if cr.saturation_index is not None:
        metrics_rows.append(
            html.Tr([html.Td("Saturation Index (SI)"), html.Td(f"{cr.saturation_index:.3f}", style={"fontWeight": "bold", "color": "#0066cc"})])
        )

    if cr.mode:
        metrics_rows.append(html.Tr([html.Td("Mode"), html.Td(cr.mode)]))

    if cr.ec50_app_str:
        metrics_rows.append(html.Tr([html.Td("EC50_app"), html.Td(cr.ec50_app_str)]))

    return html.Div([
        # Summary alert
        dbc.Alert([
            html.I(className=f"{status_icon} me-2"),
            summary
        ], color=status_color, className="mb-3"),

        dbc.Row([
            # Plot
            dbc.Col([
                dcc.Graph(figure=fig, style={'height': '400px'})
            ], md=8),

            # Metrics
            dbc.Col([
                html.H6("Analysis Metrics", className="mb-2"),
                dbc.Table([
                    html.Tbody(metrics_rows)
                ], bordered=True, hover=True, size='sm', className="mb-3"),

                # Notes
                html.Div([
                    html.Small([
                        html.I(className="fas fa-lightbulb me-1 text-warning"),
                        cr.notes
                    ], className="text-muted")
                ]) if cr.notes else None,

                # Cross-channel hint
                html.Div([
                    html.Small([
                        html.I(className="fas fa-info-circle me-1"),
                        "For validation, consider checking SFQ behavior across channels (330/350)."
                    ], className="text-muted mt-2")
                ])
            ], md=4)
        ])
    ])


def _create_ec50_results_ui_from_data(data):
    """Reconstruct EC50 results display from stored dictionary"""
    if not data or 'ec50' not in data:
        return html.Div()

    ec50 = data['ec50']
    fit_result = {
        'ec50_ci': data.get('ec50_ci', [0, 0]),
        'r2': data.get('r2', 0),
        'bottom': data.get('bottom', 0),
        'top': data.get('top', 0),
        'hill_slope': data.get('hill_slope', 0)
    }
    
    ec50_str = f"{ec50:.2e} M"
    if ec50 >= 1e-6:
        ec50_str += f" ({ec50*1e6:.2f} µM)"
    elif ec50 >= 1e-9:
        ec50_str += f" ({ec50*1e9:.2f} nM)"

    ci_str = f"{fit_result['ec50_ci'][0]:.2e} - {fit_result['ec50_ci'][1]:.2e} M"
    
    qc_flag = data.get('qc_flag', '')
    qc_message = data.get('qc_message', '')
    qc_score = data.get('qc_score', 0)
    qc_tooltip = data.get('qc_tooltip', '')

    if qc_flag == '✅':
        qc_color = 'success'
        qc_badge_color = 'success'
    elif qc_flag == '⚠️':
        qc_color = 'warning'
        qc_badge_color = 'warning'
    else:
        qc_color = 'danger'
        qc_badge_color = 'danger'

    # Recalculate derived metrics for display
    dynamic_range_degc = abs(fit_result['top'] - fit_result['bottom'])
    tm_values = np.array(data.get('tm_values', []))
    data_coverage_pct = 0.0
    if len(tm_values) > 0 and dynamic_range_degc > 0:
        experimental_range = tm_values.max() - tm_values.min()
        data_coverage_pct = (experimental_range / dynamic_range_degc) * 100.0

    return html.Div([
        dbc.Alert("✅ EC50 Analysis Complete (Restored)", color="success", className="mb-3"),

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
                html.Span(f"Score: {qc_score:.1f}/100", className="text-muted small")
            ]),
            html.Div([
                html.Small(qc_message, className="text-muted")
            ], className="mt-1") if qc_message else None,
            html.Div([
                html.Small(qc_tooltip, className="mt-2 d-block")
            ]) if qc_tooltip else None
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
                    html.Td(f"{data.get('n_points', 0)}")
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


def _create_sfq_results_ui_from_data(sfq_result_dict, sfq_figure):
    """Reconstruct SFQ results UI from stored dictionary"""
    if not sfq_result_dict:
        return _create_sfq_default_content()

    status = sfq_result_dict.get('dataset_status', 'Not detected')
    notes = sfq_result_dict.get('notes', '')
    
    # Determine status color and icon
    if status == 'Not detected':
        # Distinguish between non-specific binding (yellow) vs truly no signal (gray)
        if notes and 'Non-specific model fits equally well' in notes:
            # Non-specific binding detected - use yellow
            status_color = 'warning'
            status_icon = 'fas fa-exclamation-triangle'
        else:
            # Truly no signal or other failure - use gray
            status_color = 'secondary'
            status_icon = 'fas fa-minus-circle'
    elif status == 'Detected':
        status_color = 'success'
        status_icon = 'fas fa-check-circle'
    else:  # Detected (caution)
        status_color = 'warning'
        status_icon = 'fas fa-exclamation-triangle'

    # Reconstruct summary text roughly or use stored values
    # We'll just build a basic summary string if we can't fully reconstruct format_sfq_summary
    summary = f"SFQ Effect: {status}"
    if sfq_result_dict.get('mode'):
        summary += f" ({sfq_result_dict['mode']})"

    # Build metrics table rows
    metrics_rows = [
        html.Tr([html.Td("Status"), html.Td(dbc.Badge(status, color=status_color))]),
        html.Tr([html.Td("Signal Change"), html.Td(f"{sfq_result_dict.get('span', 0):.1f}%")]),
        html.Tr([html.Td("ΔAIC (non-specific - 4PL)"), html.Td(f"{sfq_result_dict.get('delta_aic', 0):.1f}")]),
    ]


    # Show SI as the primary and only saturation metric
    if sfq_result_dict.get('saturation_index') is not None:
        metrics_rows.append(
            html.Tr([html.Td("Saturation Index (SI)"), html.Td(f"{sfq_result_dict['saturation_index']:.3f}", style={"fontWeight": "bold", "color": "#0066cc"})])
        )


    if sfq_result_dict.get('mode'):
        metrics_rows.append(html.Tr([html.Td("Mode"), html.Td(sfq_result_dict['mode'])]))

    if sfq_result_dict.get('ec50_app_str'):
        metrics_rows.append(html.Tr([html.Td("EC50_app"), html.Td(sfq_result_dict['ec50_app_str'])]))

    notes = sfq_result_dict.get('notes')

    return html.Div([
        # Summary alert
        dbc.Alert([
            html.I(className=f"{status_icon} me-2"),
            summary
        ], color=status_color, className="mb-3"),

        dbc.Row([
            # Plot
            dbc.Col([
                dcc.Graph(figure=sfq_figure, style={'height': '400px'}) if sfq_figure else html.Div("No Figure")
            ], md=8),

            # Metrics
            dbc.Col([
                html.H6("Analysis Metrics", className="mb-2"),
                dbc.Table([
                    html.Tbody(metrics_rows)
                ], bordered=True, hover=True, size='sm', className="mb-3"),

                # Notes
                html.Div([
                    html.Small([
                        html.I(className="fas fa-lightbulb me-1 text-warning"),
                        notes
                    ], className="text-muted")
                ]) if notes else None,

                # Cross-channel hint
                html.Div([
                    html.Small([
                        html.I(className="fas fa-info-circle me-1"),
                        "For validation, consider checking SFQ behavior across channels (330/350)."
                    ], className="text-muted mt-2")
                ])
            ], md=4)
        ])
    ])


def register_dose_response_callbacks(app: Dash) -> None:
    """Register dose-response analysis callbacks"""

    @app.callback(
        Output('dose-response-store', 'data', allow_duplicate=True),
        Input('analysis-results-store', 'data'),
        prevent_initial_call=True
    )
    def clear_dr_store_on_reanalysis(results_data):
        """Clear dose-response store when basic analysis is re-run (e.g. channel change).
        This prevents stale SFQ results from being displayed."""
        return None

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

        # 按浓度排序（低到高），无浓度的排在最后
        # Sort by concentration (low to high), put samples without concentration at the end
        sorted_results = sorted(
            enumerate(results),  # Keep track of original indices
            key=lambda x: (x[1].get('concentration') is None, x[1].get('concentration') or float('inf'))
        )

        rows = []
        auto_selected = []

        for new_idx, (original_idx, r) in enumerate(sorted_results):
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
                "quality": r.get('quality_flag', ''),
                "_original_index": original_idx  # Store original index for selection mapping
            })

            # Auto-select high quality fits (R² ≥ 0.85) with valid concentration
            if r2 is not None and r2 >= 0.85 and conc is not None and np.isfinite(conc) and conc > 0:
                auto_selected.append(new_idx)  # Use new sorted index

        hint = f"{len(rows)} total samples; auto-selected {len(auto_selected)} high-quality points (R² ≥ 0.85). Adjust selection as needed."

        return rows, auto_selected, hint

    @app.callback(
        Output('dr-peak-selector-container', 'style'),
        Output('dr-peak-selector', 'options'),
        Output('dr-peak-selector', 'value'),
        Input('analysis-results-store', 'data'),
        Input('main-tabs', 'active_tab'),
        prevent_initial_call=True
    )
    def update_peak_selector(results_data, active_tab):
        """Show/hide peak selector based on whether dual-peak data is available."""
        hidden = {"display": "none"}
        default_options = [{"label": "Primary Peak", "value": "primary"}]

        if active_tab != 'dose' or not results_data or not results_data.get('results'):
            return hidden, default_options, "primary"

        # Check if any result has additional_peaks
        has_dual_peaks = any(
            r.get('additional_peaks') and len(r.get('additional_peaks', [])) >= 2
            for r in results_data['results']
        )

        if has_dual_peaks:
            # Get representative peak info from first sample with dual peaks
            for r in results_data['results']:
                peaks = r.get('additional_peaks', [])
                if len(peaks) >= 2:
                    options = [
                        {"label": f"Peak 1 ({peaks[0]['tm']:.1f}°C)", "value": "peak_0"},
                        {"label": f"Peak 2 ({peaks[1]['tm']:.1f}°C)", "value": "peak_1"},
                    ]
                    return {"display": "inline-block"}, options, "peak_0"

        return hidden, default_options, "primary"

    @app.callback(
        Output('dr-ec50-results', 'children'),
        Output('dose-response-plot', 'figure'),
        Output('dose-response-store', 'data'),
        Output('sfq-analysis-content', 'children'),
        Output('sfq-collapse', 'is_open', allow_duplicate=True),
        Input('dr-run-btn', 'n_clicks'),
        State('analysis-results-store', 'data'),
        State('dr-selection-table', 'selected_rows'),
        State('dr-selection-table', 'data'),
        State('channel-selector', 'value'),
        State('dose-response-store', 'data'),
        State('dr-peak-selector', 'value'),
        prevent_initial_call='initial_duplicate'
    )
    def run_dose_response_analysis(n_clicks, results_data, selected_rows, table_data, channel, existing_dr_data, selected_peak):
        """Run dose-response EC50 analysis"""
        # Empty figure
        fig = go.Figure()
        fig.update_layout(template='plotly_white')

        # Check for restore first
        if not n_clicks or n_clicks == 0:
            if existing_dr_data and existing_dr_data.get('ec50') is not None:
                 # Restore
                 results_ui = _create_ec50_results_ui_from_data(existing_dr_data)
                 stored_fig = existing_dr_data.get('figure', fig)
                 sfq_ui = _create_sfq_results_ui_from_data(existing_dr_data.get('sfq_result'), existing_dr_data.get('sfq_figure'))
                 
                 sfq_open = True if existing_dr_data.get('sfq_result') else False
                 
                 return results_ui, stored_fig, no_update, sfq_ui, sfq_open
            
            # Initial state
            # If nothing stored, return empty placeholders
            return (
                html.Div(), 
                fig, 
                no_update, 
                _create_sfq_default_content(), 
                False
            )

        if not results_data or not results_data.get('results'):
            fig.add_annotation(
                text="No analysis data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return (
                html.Div([dbc.Alert("No data available for analysis.", color="warning")]),
                fig,
                None,
                _create_sfq_default_content(),
                False
            )

        if not selected_rows or len(selected_rows) < 3:
            fig.add_annotation(
                text="Select at least 3 data points to fit dose-response curve",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return (
                html.Div([dbc.Alert("Please select at least 3 data points with valid concentrations for EC50 fitting.", color="warning")]),
                fig,
                None,
                _create_sfq_default_content(),
                False
            )

        # Extract selected data
        # selected_rows contains the sorted table row indices, need to map to original indices
        results = results_data['results']
        concentrations = []
        tm_values = []
        names = []

        for sorted_row_idx in selected_rows:
            if sorted_row_idx < len(table_data):
                # Get the original index from the sorted table data
                original_idx = table_data[sorted_row_idx].get('_original_index', sorted_row_idx)

                if original_idx < len(results):
                    r = results[original_idx]
                    conc = r.get('concentration')

                    # Use selected peak Tm if dual-peak mode is active
                    if selected_peak and selected_peak.startswith('peak_'):
                        peak_idx = int(selected_peak.split('_')[1])
                        peaks = r.get('additional_peaks', [])
                        if peaks and peak_idx < len(peaks):
                            tm = peaks[peak_idx]['tm']
                        else:
                            tm = r.get('tm')  # fallback to primary
                    else:
                        tm = r.get('tm')

                    if conc is not None and tm is not None and np.isfinite(conc) and np.isfinite(tm) and conc > 0:
                        concentrations.append(conc)
                        tm_values.append(tm)
                        names.append(r.get('name', f'Sample {original_idx}'))

        if len(concentrations) < 3:
            fig.add_annotation(
                text="Insufficient valid data points (need ≥3 with valid concentration and Tm)",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return (
                html.Div([dbc.Alert("Insufficient valid data points. Need at least 3 points with valid concentration and Tm.", color="danger")]),
                fig,
                None,
                _create_sfq_default_content(),
                False
            )

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
            return (
                html.Div([dbc.Alert("EC50 fitting failed. Check data quality and concentration range.", color="danger")]),
                fig,
                None,
                _create_sfq_default_content(),
                False
            )

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

        # =====================================================
        # SFQ/SFE Analysis (Static Fluorescence Quenching/Enhancement)
        # =====================================================
        print(f"[SFQ] Starting SFQ analysis, channel={channel}")
        sfq_result = None
        sfq_content = _create_sfq_default_content()
        sfq_collapse_open = False

        # Only run SFQ for 330 or 350 channels (not ratio)
        if channel and 'ratio' not in channel.lower():
            # Build sample list for SFQ analysis using ONLY selected rows (same as EC50)
            sfq_samples = []
            for sorted_row_idx in selected_rows:
                if sorted_row_idx < len(table_data):
                    # Get the original index from the sorted table data
                    original_idx = table_data[sorted_row_idx].get('_original_index', sorted_row_idx)

                    if original_idx < len(results):
                        r = results[original_idx]
                        if r.get('concentration') and r.get('T') and r.get('F'):
                            sfq_samples.append({
                                'concentration': r['concentration'],
                                'T': r['T'],
                                'F': r['F'],
                                'name': r.get('name', '')
                            })

            print(f"[SFQ] Found {len(sfq_samples)} samples with T/F data")

            if len(sfq_samples) >= 4:
                try:
                    sfq_result = analyze_sfq_dataset(sfq_samples, channel)
                    print(f"[SFQ] Analysis result: {sfq_result.dataset_status if sfq_result else 'None'}")
                    sfq_content = _create_sfq_results_ui(sfq_result, channel)

                    # Auto-expand card when SFQ analysis completes (regardless of result)
                    sfq_collapse_open = True
                    if sfq_result.dataset_status != 'Not detected':
                        print(f"[SFQ] Detected! Auto-expanding card")
                    else:
                        print(f"[SFQ] Not detected, but showing results")
                except Exception as e:
                    print(f"[SFQ] Analysis error: {e}")
                    import traceback
                    traceback.print_exc()
                    sfq_content = html.Div([
                        dbc.Alert([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            f"SFQ analysis failed: {str(e)}"
                        ], color="danger", className="mb-0")
                    ])
            else:
                sfq_content = _create_sfq_results_ui(None, channel)
        else:
            # Ratio channel - show info message
            sfq_content = _create_sfq_results_ui(None, channel or 'ratio')

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
            'figure': fig,
            # Store SFQ figure for export (if available)
            'sfq_figure': _create_sfq_figure(sfq_result) if sfq_result else None,
            # Store SFQ results for export
            'sfq_result': {
                'dataset_status': sfq_result.dataset_status if sfq_result else None,
                'channel_name': sfq_result.channel_name if sfq_result else None,
                'mode': sfq_result.channel_result.mode if sfq_result else None,
                'ec50_app': sfq_result.channel_result.ec50_app if sfq_result else None,
                'ec50_app_str': sfq_result.channel_result.ec50_app_str if sfq_result else None,
                'span': sfq_result.channel_result.span if sfq_result else None,
                'delta_aic': sfq_result.channel_result.delta_aic if sfq_result else None,
                'saturation_index': sfq_result.channel_result.saturation_index if sfq_result else None,
                'notes': sfq_result.channel_result.notes if sfq_result else None,
            } if sfq_result else None
        }

        return results_display, fig, dose_response_data, sfq_content, sfq_collapse_open
