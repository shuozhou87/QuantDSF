#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parser module for nanoDSF data
"""
import re


def parse_concentration(filename):
    """
    Extract concentration from filename in scientific notation format
    
    Parameters:
        filename (str): Filename that may contain concentration value
        
    Returns:
        float or None: Extracted concentration as float, or None if not found
    """
    # Look for pattern like "1.00E-4" or "5E-5" in filename
    match = re.search(r'(\d+(?:\.\d+)?E[+-]\d+)', filename)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None 