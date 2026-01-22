#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF Report Exporter for QuantDSF
=================================

Generates comprehensive PDF reports with all analysis results, figures, and detailed QC metrics.
Uses ReportLab for pure Python PDF generation (no system dependencies).
"""

import io
import base64
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# Color scheme matching UI
QC_COLORS = {
    'pass': colors.HexColor('#d4edda'),      # Light green
    'warning': colors.HexColor('#fff3cd'),    # Light yellow
    'fail': colors.HexColor('#f8d7da'),       # Light red
    'header': colors.HexColor('#3498db'),     # Blue
}


def _figure_to_image(fig: go.Figure, width: int = 600, height: int = 400) -> Optional[Image]:
    """
    Convert Plotly figure to ReportLab Image object.

    Args:
        fig: Plotly figure object
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        ReportLab Image object or None if conversion fails
    """
    try:
        # Export figure to PNG bytes using kaleido
        img_bytes = fig.to_image(format='png', width=width, height=height, scale=2.5)

        # Create ReportLab Image from bytes
        img_buffer = io.BytesIO(img_bytes)
        img = Image(img_buffer, width=width/72*inch, height=height/72*inch)
        return img
    except Exception as e:
        print(f"[PDF Export] Warning: Failed to convert figure to image: {e}")
        return None


def _create_table(data: List[List[str]], col_widths: Optional[List[float]] = None,
                  header_row: bool = True) -> Table:
    """
    Create a styled table.

    Args:
        data: 2D list of table data (first row is header if header_row=True)
        col_widths: Column widths in cm (None for auto)
        header_row: Whether first row is a header

    Returns:
        Styled ReportLab Table object
    """
    t = Table(data, colWidths=[w*cm for w in col_widths] if col_widths else None)

    # Base style
    style = [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]

    # Header row style
    if header_row:
        style.extend([
            ('BACKGROUND', (0, 0), (-1, 0), QC_COLORS['header']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ])

    t.setStyle(TableStyle(style))
    return t


def _create_qc_table(data: List[List[str]], qc_col_idx: int = -1) -> Table:
    """
    Create a QC-colored table with conditional formatting.

    Args:
        data: 2D list of table data
        qc_col_idx: Column index containing QC status (✅/⚠️/❌)

    Returns:
        Styled Table with QC color coding
    """
    t = _create_table(data, header_row=True)

    # Add QC-based row coloring
    styles = []
    for i, row in enumerate(data[1:], start=1):  # Skip header
        if qc_col_idx >= 0 and qc_col_idx < len(row):
            status = row[qc_col_idx]
            if '✅' in status:
                bg_color = QC_COLORS['pass']
            elif '⚠️' in status:
                bg_color = QC_COLORS['warning']
            elif '❌' in status:
                bg_color = QC_COLORS['fail']
            else:
                continue
            styles.append(('BACKGROUND', (0, i), (-1, i), bg_color))

    if styles:
        t.setStyle(TableStyle(styles))

    return t


def _generate_title_page(settings_data: Dict, styles: Any) -> List:
    """Generate PDF title page with metadata."""
    story = []

    # Title
    title = Paragraph("<b>QuantDSF Analysis Report</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 1*cm))

    # Report metadata
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    meta_data = [
        ['Report Generated', timestamp],
        ['Analysis Method', settings_data.get('method', 'N/A')],
        ['Fluorescence Channel', settings_data.get('channel', 'N/A')],
        ['QC Enabled', 'Yes' if settings_data.get('qc_enabled', False) else 'No'],
    ]

    # Add uploaded files if available
    if settings_data.get('uploaded_files'):
        files = ', '.join(settings_data['uploaded_files'])
        meta_data.append(['Data Files', files])

    meta_table = _create_table(meta_data, col_widths=[6, 10], header_row=False)
    story.append(meta_table)
    story.append(PageBreak())

    return story


def _generate_basic_analysis_section(basic_data: Dict, figures: Dict, styles: Any) -> List:
    """Generate Basic Analysis section with results table and melting curves."""
    story = []

    # Section title
    story.append(Paragraph("<b>1. Basic Analysis Results</b>", styles['Heading1']))
    story.append(Spacer(1, 0.3*cm))

    if not basic_data or not basic_data.get('results'):
        story.append(Paragraph("No basic analysis data available.", styles['Normal']))
        story.append(PageBreak())
        return story

    # Results summary table
    results = basic_data['results']

    # Build table data
    table_data = [['Sample', 'Concentration', 'Tm (°C)', 'R²', 'Method', 'QC']]
    for r in results:
        conc_str = f"{r.get('concentration', 0):.2e} M" if r.get('concentration') else 'N/A'
        tm_str = f"{r.get('tm', 0):.1f}" if r.get('tm') else 'N/A'
        r2_str = f"{r.get('r_squared', 0):.3f}" if r.get('r_squared') else 'N/A'
        method = r.get('method', 'N/A')
        qc_flag = r.get('quality_flag', '')

        table_data.append([
            r.get('name', 'Unknown'),
            conc_str,
            tm_str,
            r2_str,
            method,
            qc_flag
        ])

    results_table = _create_qc_table(table_data, qc_col_idx=5)
    story.append(results_table)
    story.append(PageBreak())

    # Melting curves figure
    if 'melting-curves-plot' in figures:
        story.append(Paragraph("<b>Melting Curves</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*cm))
        img = _figure_to_image(figures['melting-curves-plot'], width=720, height=480)
        if img:
            story.append(img)
        story.append(PageBreak())

    # Tm distribution (if available)
    if 'tm-distribution-plot' in figures:
        story.append(Paragraph("<b>Tm Distribution</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*cm))
        img = _figure_to_image(figures['tm-distribution-plot'], width=720, height=480)
        if img:
            story.append(img)
        story.append(PageBreak())

    return story


def _generate_dose_response_section(dose_response_data: Dict, figures: Dict, styles: Any) -> List:
    """Generate Dose-Response section with EC50 results and SFQ analysis."""
    story = []

    # Section title
    story.append(Paragraph("<b>2. Dose-Response Analysis</b>", styles['Heading1']))
    story.append(Spacer(1, 0.3*cm))

    if not dose_response_data:
        story.append(Paragraph("No dose-response data available.", styles['Normal']))
        story.append(PageBreak())
        return story

    # EC50 results table
    ec50_data = [
        ['Parameter', 'Value'],
        ['EC50', f"{dose_response_data.get('ec50', 0):.2e} M"],
        ['EC50 95% CI', f"{dose_response_data.get('ec50_ci', (0, 0))[0]:.2e} - {dose_response_data.get('ec50_ci', (0, 0))[1]:.2e} M"],
        ['R²', f"{dose_response_data.get('r2', 0):.3f}"],
        ['Hill Slope', f"{dose_response_data.get('hill_slope', 0):.3f}"],
        ['Bottom (Tm0)', f"{dose_response_data.get('bottom', 0):.2f} °C"],
        ['Top (Tm∞)', f"{dose_response_data.get('top', 0):.2f} °C"],
        ['N Points', str(dose_response_data.get('n_points', 0))],
    ]
    ec50_table = _create_table(ec50_data, col_widths=[6, 10])
    story.append(ec50_table)
    story.append(Spacer(1, 0.5*cm))

    # Dose-response curve
    if 'dose-response-plot' in figures:
        story.append(Paragraph("<b>Dose-Response Curve</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*cm))
        img = _figure_to_image(figures['dose-response-plot'], width=720, height=480)
        if img:
            story.append(img)
        story.append(PageBreak())

    # SFQ/SFE Analysis (if available)
    sfq = dose_response_data.get('sfq_result')
    if sfq and sfq.get('dataset_status') != 'Not detected':
        story.append(Paragraph("<b>Static Fluorescence Quenching/Enhancement</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        sfq_data = [
            ['Parameter', 'Value'],
            ['Status', sfq.get('dataset_status', 'N/A')],
            ['Channel', f"F{sfq.get('channel_name', 'N/A')}"],
            ['Mode', sfq.get('mode', 'N/A')],
            ['EC50_app', sfq.get('ec50_app_str', 'N/A')],
            ['Dynamic Range (Span)', f"{sfq.get('span', 0):.1f}%"],
            ['ΔAIC (linear - 4PL)', f"{sfq.get('delta_aic', 0):.1f}"],
            ['Saturation Index (SI)', f"{sfq.get('saturation_index', 0):.3f}" if sfq.get('saturation_index') else 'N/A'],
        ]
        sfq_table = _create_table(sfq_data, col_widths=[8, 8])
        story.append(sfq_table)

        if sfq.get('notes'):
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph(f"<i>Note: {sfq['notes']}</i>", styles['Normal']))

        story.append(PageBreak())

    return story


def _generate_thermodynamics_section(thermodynamics_data: Dict, figures: Dict, styles: Any) -> List:
    """Generate Thermodynamics section with Van't Hoff analysis."""
    story = []

    # Section title
    story.append(Paragraph("<b>3. Thermodynamic Analysis</b>", styles['Heading1']))
    story.append(Spacer(1, 0.3*cm))

    if not thermodynamics_data:
        story.append(Paragraph("No thermodynamic data available.", styles['Normal']))
        story.append(PageBreak())
        return story

    # Van't Hoff parameters
    vh_data = [
        ['Parameter', 'Value'],
        ['ΔH', f"{thermodynamics_data.get('delta_h_display', 0):.2f} {thermodynamics_data.get('delta_h_unit', 'kJ/mol')}"],
        ['ΔS', f"{thermodynamics_data.get('delta_s_display', 0):.2f} {thermodynamics_data.get('delta_s_unit', 'J/mol·K')}"],
        ['R²', f"{thermodynamics_data.get('r2', 0):.3f}"],
        ['KD @ 298K', f"{thermodynamics_data.get('kd_298k', 0):.2e} M"],
        ['KD @ 310K', f"{thermodynamics_data.get('kd_310k', 0):.2e} M"],
        ['N Points', str(thermodynamics_data.get('n_points', 0))],
    ]
    vh_table = _create_table(vh_data, col_widths=[6, 10])
    story.append(vh_table)
    story.append(Spacer(1, 0.5*cm))

    # Van't Hoff plot
    if 'vanthoff-plot' in figures:
        story.append(Paragraph("<b>Van't Hoff Plot</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*cm))
        img = _figure_to_image(figures['vanthoff-plot'], width=720, height=480)
        if img:
            story.append(img)
        story.append(PageBreak())

    # Overlay plots
    if 'vh-overlay-plot' in figures:
        story.append(Paragraph("<b>Overlay Analysis</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*cm))
        img = _figure_to_image(figures['vh-overlay-plot'], width=720, height=480)
        if img:
            story.append(img)
        story.append(PageBreak())

    # Isothermal panels
    if 'isothermal-panels-plot' in figures:
        story.append(Paragraph("<b>Isothermal Dose-Response Panels</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*cm))
        img = _figure_to_image(figures['isothermal-panels-plot'], width=720, height=480)
        if img:
            story.append(img)
        story.append(PageBreak())

    return story


def _generate_qc_appendix(basic_data: Dict, dose_response_data: Dict,
                          thermodynamics_data: Dict, styles: Any) -> List:
    """Generate comprehensive QC appendix with detailed quality metrics."""
    story = []

    # Appendix title
    story.append(Paragraph("<b>Appendix: Quality Control Details</b>", styles['Heading1']))
    story.append(Spacer(1, 0.5*cm))

    # === APPENDIX A: Basic Analysis QC ===
    if basic_data and basic_data.get('results'):
        story.append(Paragraph("<b>A. Basic Analysis QC</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        results = basic_data['results']

        # A.1: Summary statistics
        total_samples = len(results)
        passed = sum(1 for r in results if r.get('quality_flag') == '✅')
        warned = sum(1 for r in results if r.get('quality_flag') == '⚠️')
        failed = sum(1 for r in results if r.get('quality_flag') == '❌')
        pass_rate = (passed / total_samples * 100) if total_samples > 0 else 0

        summary_text = f"""
        <b>Summary Statistics:</b><br/>
        Total Samples: {total_samples}<br/>
        Passed (✅): {passed} ({pass_rate:.1f}%)<br/>
        Warned (⚠️): {warned}<br/>
        Failed (❌): {failed}
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # A.2: Per-sample QC table
        story.append(Paragraph("<b>A.2 Per-Sample QC Metrics</b>", styles['Heading3']))
        story.append(Spacer(1, 0.2*cm))

        qc_table_data = [['Sample', 'Tm', 'R²', 'Method', 'QC Score', 'Status']]
        for r in results:
            qc_table_data.append([
                r.get('name', 'Unknown')[:20],  # Truncate long names
                f"{r.get('tm', 0):.1f}" if r.get('tm') else 'N/A',
                f"{r.get('r_squared', 0):.3f}" if r.get('r_squared') else 'N/A',
                r.get('method', 'N/A'),
                f"{r.get('qc_score', 0):.1f}" if r.get('qc_score') is not None else 'N/A',
                r.get('quality_flag', '')
            ])

        qc_table = _create_qc_table(qc_table_data, qc_col_idx=5)
        story.append(qc_table)
        story.append(PageBreak())

    # === APPENDIX B: Dose-Response QC ===
    if dose_response_data and dose_response_data.get('ec50'):
        story.append(Paragraph("<b>B. Dose-Response QC</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        dr_qc_data = [
            ['QC Metric', 'Value'],
            ['QC Flag', dose_response_data.get('qc_flag', 'N/A')],
            ['QC Score', f"{dose_response_data.get('qc_score', 0):.1f}" if dose_response_data.get('qc_score') is not None else 'N/A'],
            ['QC Message', dose_response_data.get('qc_message', 'N/A')],
        ]
        dr_qc_table = _create_table(dr_qc_data, col_widths=[6, 10])
        story.append(dr_qc_table)
        story.append(Spacer(1, 0.5*cm))

        # SFQ details if available
        sfq = dose_response_data.get('sfq_result')
        if sfq:
            story.append(Paragraph("<b>B.2 SFQ/SFE Analysis Details</b>", styles['Heading3']))
            story.append(Spacer(1, 0.2*cm))

            sfq_detail_data = [
                ['Parameter', 'Value'],
                ['Detection Status', sfq.get('dataset_status', 'N/A')],
                ['Mode', sfq.get('mode', 'N/A') if sfq.get('mode') else 'Not detected'],
                ['Span (%)', f"{sfq.get('span', 0):.1f}"],
                ['ΔAIC', f"{sfq.get('delta_aic', 0):.1f}"],
                ['Saturation Index', f"{sfq.get('saturation_index', 0):.3f}" if sfq.get('saturation_index') else 'N/A'],
                ['Notes', sfq.get('notes', 'None')],
            ]
            sfq_detail_table = _create_table(sfq_detail_data, col_widths=[6, 10])
            story.append(sfq_detail_table)

        story.append(PageBreak())

    # === APPENDIX C: Thermodynamics QC ===
    if thermodynamics_data and thermodynamics_data.get('delta_h'):
        story.append(Paragraph("<b>C. Thermodynamics QC</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        thermo_qc_data = [
            ['QC Metric', 'Value'],
            ['QC Flag', thermodynamics_data.get('qc_flag', 'N/A')],
            ['QC Score', f"{thermodynamics_data.get('qc_score', 0):.1f}" if thermodynamics_data.get('qc_score') is not None else 'N/A'],
            ['QC Message', thermodynamics_data.get('qc_message', 'N/A')],
        ]

        # Add QC details if available
        qc_details = thermodynamics_data.get('qc_details', {})
        if qc_details:
            thermo_qc_data.extend([
                ['Van\'t Hoff R²', f"{qc_details.get('vh_r2', 0):.3f}"],
                ['Temperature Range', f"{qc_details.get('delta_T', 0):.1f} °C"],
                ['ΔH Relative Error', f"{qc_details.get('dH_rel_err', 0)*100:.1f}%" if qc_details.get('dH_rel_err') is not None else 'N/A'],
                ['ΔS Relative Error', f"{qc_details.get('dS_rel_err', 0)*100:.1f}%" if qc_details.get('dS_rel_err') is not None else 'N/A'],
                ['KD@298K Reliability', qc_details.get('reliability_298', 'N/A')],
                ['KD@310K Reliability', qc_details.get('reliability_310', 'N/A')],
            ])

        thermo_qc_table = _create_table(thermo_qc_data, col_widths=[6, 10])
        story.append(thermo_qc_table)
        story.append(PageBreak())

    return story


def create_pdf_report(
    basic_data: Dict,
    dose_response_data: Dict,
    thermodynamics_data: Dict,
    settings_data: Dict,
    figures: Dict[str, go.Figure]
) -> Tuple[bytes, str]:
    """
    Generate comprehensive PDF report with all analysis results.

    Args:
        basic_data: Basic analysis results from analysis-results-store
        dose_response_data: Dose-response results from dose-response-store
        thermodynamics_data: Thermodynamics results from thermodynamics-store
        settings_data: Analysis settings and metadata
        figures: Dictionary of Plotly figure objects keyed by plot ID

    Returns:
        Tuple of (pdf_bytes, filename)
    """
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # Get styles
    styles = getSampleStyleSheet()

    # Build story (content)
    story = []

    # Title page
    story.extend(_generate_title_page(settings_data, styles))

    # Main sections
    story.extend(_generate_basic_analysis_section(basic_data, figures, styles))
    story.extend(_generate_dose_response_section(dose_response_data, figures, styles))
    story.extend(_generate_thermodynamics_section(thermodynamics_data, figures, styles))

    # QC Appendix
    story.extend(_generate_qc_appendix(basic_data, dose_response_data, thermodynamics_data, styles))

    # Build PDF
    doc.build(story)

    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Generate filename
    filename = f"QuantDSF_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return pdf_bytes, filename
