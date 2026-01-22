# Advanced Settings - TSB Smoothing Feature

**Date**: 2025-12-13
**Version**: QuantDSF v2.0
**Status**: Implemented and Tested

## Overview

Added an Advanced Settings panel to allow users to optionally enable TSB (Two-State Boltzmann) model-based smoothing for the First Derivative (FD) method. This addresses the scientific concern that using TSB analytical derivatives by default would compromise the independence of the FD method.

## Problem Context

### Discovery
When investigating why TSB smoothing wasn't working for the FD method, we discovered it was actually working perfectly:
- All 16 samples showed R² values between 0.9994-0.9999 for TSB fits
- FD method Tm values (73.5-77.6°C) matched TSB method values exactly
- This was because FD was using TSB model's analytical derivative instead of numerical Savitzky-Golay filtering

### Scientific Issue
Using TSB analytical derivatives for FD method is problematic because:
1. **Loses method independence**: FD and TSB methods should be independent for validation
2. **Circular dependency**: FD results depend on TSB model fitting
3. **"Cheating"**: The FD method is no longer a true independent measurement

### Solution
Make TSB smoothing an **optional** feature that:
- Defaults to `False` to preserve method independence
- Can be enabled as an advanced option when users want maximum smoothness
- Is clearly labeled as "experimental" to indicate trade-offs

## Implementation

### UI Changes

#### New Component: Advanced Settings Panel

**Location**: [app/components/sidebar.py:210-227](app/components/sidebar.py#L210-L227)

```python
def _create_advanced_settings() -> html.Div:
    """高级设置选项"""
    return html.Div([
        html.Div([
            html.Label("First Derivative Method", className="fw-bold small mb-2"),
            dbc.Checkbox(
                id="fd-use-tsb-smoothing-checkbox",
                label="Use TSB model for smoothing (experimental)",
                value=False,  # Default to False for method independence
                className="mb-2"
            ),
            html.Small(
                "When enabled, uses TSB analytical derivative instead of Savitzky-Golay filter. "
                "Provides smoother curves but reduces method independence.",
                className="text-muted"
            ),
        ]),
    ])
```

#### Integration into Van't Hoff Parameters Panel

**Location**: [app/components/sidebar.py:199-207](app/components/sidebar.py#L199-L207)

The Advanced Settings panel is integrated as a **nested accordion** inside the Van't Hoff Parameters accordion:

```python
# Advanced Settings 子折叠面板
dbc.Accordion([
    dbc.AccordionItem([
        _create_advanced_settings()
    ], title="⚙️ Advanced Settings")
], start_collapsed=True, className="mt-3"),
```

**UI Hierarchy**:
```
📊 Van't Hoff Parameters (accordion)
├── Use Van't Hoff Equation (checkbox)
├── ΔH Reference Temperature (input)
├── Enable ΔCp fitting (checkbox)
└── ⚙️ Advanced Settings (nested accordion, collapsed by default)
    └── First Derivative Method
        └── Use TSB model for smoothing (checkbox, default=False)
```

### Backend Changes

#### Callback Integration

**Location**: [app/callbacks/analysis_callbacks.py:120](app/callbacks/analysis_callbacks.py#L120)

Added new State parameter to capture checkbox value:

```python
@app.callback(
    Output('analysis-results-store', 'data'),
    Output('results-table-container', 'children'),
    Output('melting-curves-plot', 'figure'),
    Output('tm-distribution-plot', 'figure'),
    Output('derivative-curves-plot', 'figure', allow_duplicate=True),
    Output('derivative-panel', 'style', allow_duplicate=True),
    Input('run-analysis-btn', 'n_clicks'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('method-selector', 'value'),
    State('channel-selector', 'value'),
    State('fd-use-tsb-smoothing-checkbox', 'value'),  # NEW
    State('analysis-results-store', 'data'),
    prevent_initial_call=True
)
def run_tm_analysis(n_clicks, contents_list, filenames, method, channel,
                    use_tsb_smoothing, previous_results_data):
```

#### Derivative Computation

**Location**: [app/callbacks/analysis_callbacks.py:219-224](app/callbacks/analysis_callbacks.py#L219-L224)

Changed from hardcoded `use_tsb_smoothing=True` to dynamic value from checkbox:

```python
else:  # derivative
    from core.analysis.tm import compute_derivative, find_derivative_peaks

    # compute_derivative with optional TSB smoothing
    # use_tsb_smoothing is controlled by Advanced Settings checkbox (default: False)
    T_deriv, deriv = compute_derivative(T, F, use_tsb_smoothing=use_tsb_smoothing or False)
```

### Core Logic (Already Implemented)

The TSB smoothing logic in [core/analysis/tm/derivative.py:73-127](core/analysis/tm/derivative.py#L73-L127) was already implemented. Key behavior:

1. **When `use_tsb_smoothing=True`**:
   - Attempts TSB model fit
   - If successful and R² > 0.85, uses TSB analytical derivative
   - If failed or R² ≤ 0.85, falls back to Savitzky-Golay filter
   - Logs all attempts to `tsb_smoothing_debug.log`

2. **When `use_tsb_smoothing=False` (default)**:
   - Uses traditional Savitzky-Golay filtering
   - Maintains complete independence from TSB method

## Files Modified

1. **[app/components/sidebar.py](app/components/sidebar.py)**
   - Added `_create_advanced_settings()` function
   - Modified `_create_thermodynamic_settings()` to include nested Advanced Settings accordion

2. **[app/callbacks/analysis_callbacks.py](app/callbacks/analysis_callbacks.py)**
   - Added `State('fd-use-tsb-smoothing-checkbox', 'value')` to callback
   - Added `use_tsb_smoothing` parameter to `run_tm_analysis()` function
   - Modified `compute_derivative()` call to use checkbox value

3. **[core/analysis/tm/derivative.py](core/analysis/tm/derivative.py)** (previously fixed)
   - Fixed import path: `from .boltzmann import` (not `from ..boltzmann import`)
   - Fixed Unicode encoding errors in debug logging
   - TSB smoothing logic already implemented

## Testing Recommendations

### Test Case 1: Default Behavior (TSB Smoothing OFF)
1. Load sample data with good TSB fits (R² > 0.99)
2. Ensure Advanced Settings checkbox is **unchecked** (default)
3. Run FD analysis
4. **Expected**: FD Tm values should differ slightly from TSB Tm values
5. **Expected**: No `tsb_smoothing_debug.log` entries (TSB smoothing not attempted)

### Test Case 2: TSB Smoothing Enabled
1. Load same sample data
2. Expand Advanced Settings and **check** the TSB smoothing checkbox
3. Run FD analysis
4. **Expected**: FD Tm values should match TSB Tm values closely
5. **Expected**: `tsb_smoothing_debug.log` shows successful TSB smoothing with high R² values

### Test Case 3: TSB Smoothing with Poor Fits
1. Load data with poor TSB fits (R² < 0.85)
2. Enable TSB smoothing
3. Run FD analysis
4. **Expected**: Falls back to Savitzky-Golay filter
5. **Expected**: `tsb_smoothing_debug.log` shows "[FAILED] Falling back to SG filter"

## Design Rationale

### Why Nested Accordion?
- **Scalability**: Allows adding more advanced options in the future
- **Clean UI**: Keeps advanced features hidden by default
- **Logical grouping**: Advanced settings are related to thermodynamic analysis
- **User expectation**: Users looking for Van't Hoff settings will find Advanced Settings nearby

### Why Default to False?
- **Scientific integrity**: Method independence is critical for validation
- **Conservative approach**: Users must explicitly opt-in to experimental features
- **Transparency**: Forces users to understand the trade-off before enabling

### Why Labeled "Experimental"?
- **Honest communication**: This feature has trade-offs (smoothness vs. independence)
- **User awareness**: Prevents casual enabling without understanding implications
- **Future flexibility**: Can remove label if feature becomes standard practice

## Future Enhancements

The Advanced Settings panel is designed to accommodate future options:

### Potential Future Settings
1. **Savitzky-Golay filter parameters**:
   - Window size (currently hardcoded)
   - Polynomial order (currently hardcoded)

2. **Derivative calculation options**:
   - Numerical differentiation method (forward/backward/central)
   - Temperature step size

3. **Peak detection options**:
   - Minimum peak prominence
   - Peak width constraints
   - Multiple peak detection

4. **Data preprocessing**:
   - Baseline correction methods
   - Outlier detection/removal
   - Temperature range restrictions

### Implementation Pattern
To add new advanced settings:

1. Add new control to `_create_advanced_settings()` function:
```python
def _create_advanced_settings() -> html.Div:
    return html.Div([
        html.Div([
            html.Label("First Derivative Method", className="fw-bold small mb-2"),
            # ... existing TSB smoothing checkbox ...
        ]),

        html.Hr(),  # Separator

        html.Div([
            html.Label("New Feature Category", className="fw-bold small mb-2"),
            # ... new controls ...
        ]),
    ])
```

2. Add corresponding State parameter to callback
3. Pass parameter to relevant analysis function

## Related Documentation

- **[FD_METHOD_FIX_2025.md](FD_METHOD_FIX_2025.md)**: Original FD method bug fix (peak detection algorithm)
- **[core/analysis/tm/derivative.py](../core/analysis/tm/derivative.py)**: Core derivative calculation with TSB smoothing logic
- **[core/analysis/tm/boltzmann.py](../core/analysis/tm/boltzmann.py)**: TSB model fitting and analytical derivatives

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-13 | 1.0 | Initial implementation of Advanced Settings with TSB smoothing option |

## Known Issues

None currently.

## Notes

- The TSB smoothing feature was discovered to be working "too well" during debugging, prompting this implementation
- Debug logging to `tsb_smoothing_debug.log` is still active and can be used for troubleshooting
- Unicode encoding issues in Windows console were fixed by using ASCII alternatives ([SUCCESS]/[FAILED] instead of ✓/✗)
