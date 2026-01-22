#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complete Export Package
========================
Orchestrate complete export of all analysis results and figures to ZIP package.

Package Structure:
    QuantDSF_Export_YYYYMMDD_HHMMSS.zip
    ├── QuantDSF_Results.xlsx (4 sheets)
    ├── Basic_Analysis_1.png
    ├── Basic_Analysis_2.png
    ├── Dose_Response_1.png
    ├── Thermodynamics_1.png
    ├── Thermodynamics_2.png
    └── Thermodynamics_3.png
"""

import io
import zipfile
from datetime import datetime
from typing import Optional, Dict, Any, List
import plotly.graph_objects as go

from .excel_exporter import create_excel_workbook
from .figure_exporter import export_figure_by_id, is_figure_empty
from .pdf_report_exporter import create_pdf_report


def create_complete_export_package(
    basic_data: Optional[Dict[str, Any]] = None,
    dose_response_data: Optional[Dict[str, Any]] = None,
    thermodynamics_data: Optional[Dict[str, Any]] = None,
    settings_data: Optional[Dict[str, Any]] = None,
    figures: Optional[Dict[str, go.Figure]] = None
) -> tuple[bytes, str]:
    """
    Create complete export package with Excel and PNG figures.

    Args:
        basic_data: Basic analysis results from analysis-results-store
        dose_response_data: EC50 analysis results from dose-response-store
        thermodynamics_data: Van't Hoff results from thermodynamics-store
        settings_data: Analysis settings and metadata
        figures: Dictionary mapping figure IDs to Plotly figure objects
                 e.g., {'melting-curves-plot': fig, 'dose-response-plot': fig2, ...}

    Returns:
        Tuple of (zip_bytes, zip_filename)
            zip_bytes: Complete ZIP package as bytes
            zip_filename: Suggested filename with timestamp

    Example:
        >>> zip_bytes, filename = create_complete_export_package(
        ...     basic_data=basic_results,
        ...     figures={'melting-curves-plot': fig1, 'dose-response-plot': fig2}
        ... )
        >>> # filename = 'QuantDSF_Export_20260110_143022.zip'
        >>> with open(filename, 'wb') as f:
        ...     f.write(zip_bytes)

    Package Contents:
        - QuantDSF_Results.xlsx: 4-sheet workbook
        - PNG files for all non-empty figures (300 DPI)

    Notes:
        - Empty/placeholder figures are NOT included in ZIP
        - Excel is always included (with placeholder sheets if needed)
        - Filename includes timestamp to prevent overwriting
    """
    # Create ZIP buffer
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Add Excel workbook
        excel_bytes = create_excel_workbook(
            basic_data=basic_data,
            dose_response_data=dose_response_data,
            thermodynamics_data=thermodynamics_data,
            settings_data=settings_data
        )
        zf.writestr('QuantDSF_Results.xlsx', excel_bytes)

        # 2. Add PNG figures (skip empty ones)
        if figures:
            for figure_id, fig in figures.items():
                # Skip if figure is empty
                if is_figure_empty(fig):
                    continue

                # Export figure
                result = export_figure_by_id(figure_id, fig)
                if result:
                    filename, png_bytes = result
                    zf.writestr(filename, png_bytes)

    # Generate timestamped filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f'QuantDSF_Export_{timestamp}.zip'

    zip_buffer.seek(0)
    return zip_buffer.getvalue(), zip_filename


def create_export_manifest(
    basic_data: Optional[Dict[str, Any]] = None,
    dose_response_data: Optional[Dict[str, Any]] = None,
    thermodynamics_data: Optional[Dict[str, Any]] = None,
    figures: Optional[Dict[str, go.Figure]] = None
) -> Dict[str, Any]:
    """
    Generate export manifest describing what will be included in package.

    Args:
        basic_data: Basic analysis results
        dose_response_data: Dose-response results
        thermodynamics_data: Thermodynamics results
        figures: Dictionary of figure objects

    Returns:
        Manifest dictionary with export summary

    Example:
        >>> manifest = create_export_manifest(basic_data=data, figures=figs)
        >>> manifest
        {
            'timestamp': '2026-01-10 14:30:22',
            'excel_sheets': ['Basic_Analysis', 'Dose_Response', 'Thermodynamics', 'Analysis_Settings'],
            'has_basic_data': True,
            'has_dose_response_data': False,
            'has_thermodynamics_data': False,
            'figures_included': ['Basic_Analysis_1.png', 'Basic_Analysis_2.png'],
            'figures_skipped': ['Dose_Response_1.png'],
            'total_files': 3
        }

    Notes:
        Useful for showing user what will be exported before actual export
    """
    manifest = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'excel_sheets': ['Basic_Analysis', 'Dose_Response', 'Thermodynamics', 'Analysis_Settings'],
        'has_basic_data': basic_data is not None and len(basic_data.get('results', [])) > 0,
        'has_dose_response_data': dose_response_data is not None and dose_response_data.get('ec50') is not None,
        'has_thermodynamics_data': thermodynamics_data is not None and thermodynamics_data.get('delta_h') is not None,
        'figures_included': [],
        'figures_skipped': [],
        'total_files': 1  # Excel always included
    }

    # Check figures
    if figures:
        from .figure_exporter import FIGURE_MAPPING

        for figure_id, fig in figures.items():
            if figure_id in FIGURE_MAPPING:
                filename = FIGURE_MAPPING[figure_id]
                if is_figure_empty(fig):
                    manifest['figures_skipped'].append(filename)
                else:
                    manifest['figures_included'].append(filename)
                    manifest['total_files'] += 1

    return manifest


def validate_export_data(
    basic_data: Optional[Dict[str, Any]] = None,
    dose_response_data: Optional[Dict[str, Any]] = None,
    thermodynamics_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate export data and provide warnings/errors.

    Args:
        basic_data: Basic analysis results
        dose_response_data: Dose-response results
        thermodynamics_data: Thermodynamics results

    Returns:
        Validation result dictionary

    Example:
        >>> validation = validate_export_data(basic_data=data)
        >>> validation
        {
            'valid': True,
            'warnings': ['No Dose-Response analysis run'],
            'errors': [],
            'can_export': True
        }

    Notes:
        - Export is always allowed (even with all empty data)
        - Warnings indicate missing analyses
        - Errors would indicate data corruption (rarely happens)
    """
    warnings = []
    errors = []

    # Check Basic Analysis
    if not basic_data or not basic_data.get('results') or len(basic_data['results']) == 0:
        warnings.append('No Basic Analysis results available')

    # Check Dose-Response
    if not dose_response_data or dose_response_data.get('ec50') is None:
        warnings.append('No Dose-Response analysis run')

    # Check Thermodynamics
    if not thermodynamics_data or thermodynamics_data.get('delta_h') is None:
        warnings.append('No Thermodynamics analysis run')

    # All warnings scenario
    if len(warnings) == 3:
        warnings.append('Export will contain only empty placeholder tables')

    return {
        'valid': len(errors) == 0,
        'warnings': warnings,
        'errors': errors,
        'can_export': True  # Always allow export
    }


def create_pdf_export(
    basic_data: Optional[Dict[str, Any]] = None,
    dose_response_data: Optional[Dict[str, Any]] = None,
    thermodynamics_data: Optional[Dict[str, Any]] = None,
    settings_data: Optional[Dict[str, Any]] = None,
    figures: Optional[Dict[str, go.Figure]] = None
) -> tuple[bytes, str]:
    """
    Create PDF report export (alternative to ZIP package).

    Args:
        basic_data: Basic analysis results from analysis-results-store
        dose_response_data: Dose-response results from dose-response-store
        thermodynamics_data: Thermodynamics results from thermodynamics-store
        settings_data: Analysis settings and metadata
        figures: Dictionary of figure objects keyed by plot ID

    Returns:
        Tuple of (pdf_bytes, filename)

    Example:
        >>> pdf_bytes, filename = create_pdf_export(
        ...     basic_data=basic_data,
        ...     dose_response_data=dr_data,
        ...     figures=figures
        ... )
        >>> # Returns: (b'%PDF-1.4...', 'QuantDSF_Report_20260120_143052.pdf')
    """
    return create_pdf_report(
        basic_data=basic_data or {},
        dose_response_data=dose_response_data or {},
        thermodynamics_data=thermodynamics_data or {},
        settings_data=settings_data or {},
        figures=figures or {}
    )
