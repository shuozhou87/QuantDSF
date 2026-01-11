#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Result Exporters
=================
结果导出模块

Export Package Structure:
- excel_exporter: Create formatted 4-sheet Excel workbook
- figure_exporter: Export Plotly figures to PNG at 300 DPI
- complete_exporter: Orchestrate complete ZIP package export
"""

from .excel_exporter import create_excel_workbook
from .figure_exporter import (
    export_plotly_to_png,
    export_figure_by_id,
    is_figure_empty,
    get_all_figure_mappings,
    FIGURE_MAPPING
)
from .complete_exporter import create_complete_export_package

__all__ = [
    # Excel export
    'create_excel_workbook',

    # Figure export
    'export_plotly_to_png',
    'export_figure_by_id',
    'is_figure_empty',
    'get_all_figure_mappings',
    'FIGURE_MAPPING',

    # Complete package export
    'create_complete_export_package',
]


