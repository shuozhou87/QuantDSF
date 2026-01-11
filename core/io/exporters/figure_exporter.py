#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Figure Exporter
================
Export Plotly figures to PNG format for inclusion in export packages.
"""

import io
from typing import Dict, Optional
import plotly.graph_objects as go


# Figure ID to filename mapping
FIGURE_MAPPING = {
    # Basic Analysis
    'melting-curves-plot': 'Basic_Analysis_1.png',
    'tm-distribution-plot': 'Basic_Analysis_2.png',

    # Dose Response (only 1 plot in actual implementation)
    'dose-response-plot': 'Dose_Response_1.png',

    # Thermodynamics
    'vanthoff-plot': 'Thermodynamics_1.png',
    'vh-overlay-plot': 'Thermodynamics_2.png',
    'isothermal-panels-plot': 'Thermodynamics_3.png',
}


def export_plotly_to_png(
    fig: go.Figure,
    width: int = 1200,
    height: int = 800,
    scale: float = 2.5
) -> bytes:
    """
    Export a Plotly figure to PNG bytes at 300 DPI.

    Args:
        fig: Plotly figure object
        width: Width in pixels (default 1200)
        height: Height in pixels (default 800)
        scale: Scale factor for DPI (2.5 = 300 DPI at standard screen resolution)

    Returns:
        PNG image as bytes

    Raises:
        ImportError: If kaleido is not installed
        RuntimeError: If PNG export fails

    Notes:
        - Requires kaleido library: `pip install kaleido`
        - Scale 2.5 with 1200x800 px = 300 DPI (publication quality)
        - On Windows, kaleido should work out of box
        - On Linux/Mac, may require Chrome/Chromium installed
    """
    try:
        # Use in-memory buffer
        img_bytes = io.BytesIO()

        # Write image using kaleido
        # Scale controls DPI: 1.0 = 96 DPI, 2.5 = 240-300 DPI
        fig.write_image(
            img_bytes,
            format='png',
            width=width,
            height=height,
            scale=scale,
            engine='kaleido'
        )

        img_bytes.seek(0)
        return img_bytes.read()

    except ImportError as e:
        raise ImportError(
            "Kaleido library is required for PNG export. "
            "Install with: pip install kaleido"
        ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to export figure to PNG: {str(e)}") from e


def export_figure_by_id(
    figure_id: str,
    fig: go.Figure,
    width: int = 1200,
    height: int = 800
) -> Optional[tuple[str, bytes]]:
    """
    Export a figure with automatic filename mapping.

    Args:
        figure_id: Graph component ID (e.g., 'melting-curves-plot')
        fig: Plotly figure object
        width: Width in pixels
        height: Height in pixels

    Returns:
        Tuple of (filename, png_bytes) if figure_id is mapped, None otherwise

    Example:
        >>> fig = go.Figure(...)
        >>> result = export_figure_by_id('melting-curves-plot', fig)
        >>> if result:
        >>>     filename, png_bytes = result
        >>>     # filename = 'Basic_Analysis_1.png'
    """
    if figure_id not in FIGURE_MAPPING:
        return None

    filename = FIGURE_MAPPING[figure_id]
    png_bytes = export_plotly_to_png(fig, width=width, height=height)

    return filename, png_bytes


def is_figure_empty(fig: go.Figure) -> bool:
    """
    Check if a Plotly figure is empty or contains only placeholder text.

    Args:
        fig: Plotly figure object

    Returns:
        True if figure is empty or placeholder, False if it has real data

    Notes:
        - Checks if figure has no traces (data)
        - Also checks for annotation-only figures (placeholder text)
    """
    # No data traces
    if not fig.data or len(fig.data) == 0:
        return True

    # Check if all traces are empty
    all_empty = all(
        (not hasattr(trace, 'x') or len(trace.x) == 0) and
        (not hasattr(trace, 'y') or len(trace.y) == 0)
        for trace in fig.data
    )

    return all_empty


def get_all_figure_mappings() -> Dict[str, str]:
    """
    Get complete mapping of figure IDs to export filenames.

    Returns:
        Dictionary mapping figure component IDs to export filenames
    """
    return FIGURE_MAPPING.copy()
