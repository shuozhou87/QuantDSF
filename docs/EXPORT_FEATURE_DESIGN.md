# Export Feature Design Document
# 导出功能设计文档

**Version**: 2.0 (Revised)
**Date**: 2026-01-10
**Status**: Ready for Implementation

---

## 📋 Executive Summary

Export functionality is a **critical user requirement** for QuantDSF. Users (primarily biochemical scientists) need a simple, one-click solution to export all analysis results, QC metrics, and visualizations.

**Design Philosophy**:
- **One-Click Export** - Single large "Export Results" button
- **Complete Package** - All tabs, all data, all figures in one ZIP
- **Excel-First** - Scientists prefer spreadsheets over CSV
- **Publication-Ready** - High-resolution PNG figures (300 DPI)

---

## 🎯 Finalized User Requirements

### Core Requirement

**One-Click Complete Export**:
- Users click a single "📊 Export Results" button
- System generates a ZIP file containing:
  - **Excel workbook** with all analysis results, QC metrics, and settings
  - **PNG figures** for all generated plots (300 DPI)
- Download starts automatically

### User Workflow

1. User uploads data and runs Basic Analysis (minimum requirement)
2. Optionally runs Dose-Response and/or Thermodynamics analysis
3. Clicks "Export Results" button in sidebar
4. Receives `QuantDSF_Export_YYYYMMDD_HHMMSS.zip`
5. Unzips to find:
   - `QuantDSF_Results.xlsx` (multi-sheet workbook)
   - `Basic_Analysis_1.png`, `Basic_Analysis_2.png`, ...
   - `Dose_Response_1.png`, ... (if analysis was run)
   - `Thermodynamics_1.png`, ... (if analysis was run)

---

## 🏗️ System Architecture

### Export Data Flow

```
User Click → Dash Callback → Data Aggregation → Format Conversion → File Download
                ↓
        Session State/Cache
                ↓
        Analysis Results
```

### Module Structure

```
core/io/exporters/
├── __init__.py
├── base_exporter.py          # Abstract base class
├── csv_exporter.py            # CSV format (MISSING - TO CREATE)
├── excel_exporter.py          # Excel workbook (EXISTS - ENHANCE)
├── figure_exporter.py         # Image export utilities (NEW)
└── qc_report_exporter.py      # QC summary reports (NEW)

app/callbacks/
├── export_callbacks.py        # Export button callbacks (EXISTS - EXPAND)

app/layouts/
├── basic_analysis.py          # Add export section
├── dose_response.py           # Add export section
└── thermodynamic.py           # Enhance existing export section
```

---

## 📦 Export Package Specification

### ZIP Archive Structure

**Filename**: `QuantDSF_Export_YYYYMMDD_HHMMSS.zip`

**Contents**:
```
QuantDSF_Export_20260110_143052.zip
├── QuantDSF_Results.xlsx          # Multi-sheet Excel workbook
├── Basic_Analysis_1.png           # Melting curves plot
├── Basic_Analysis_2.png           # Tm distribution plot (if exists)
├── Dose_Response_1.png            # EC50 vs Temperature plot (if analysis run)
├── Dose_Response_2.png            # Dose-response curves grid (if exists)
├── Thermodynamics_1.png           # Van't Hoff plot (if analysis run)
├── Thermodynamics_2.png           # Normalized AUC overlay (if exists)
└── Thermodynamics_3.png           # Isothermal dose-response panels (if exists)
```

### Excel Workbook Structure

**File**: `QuantDSF_Results.xlsx`

**Sheets** (following tab names from UI):

#### Sheet 1: `Basic_Analysis`
**Content**: Tm results table for all capillaries

| Sample | Concentration (M) | Tm (°C) | Tm Error (°C) | R² | Method | QC Status | QC Flag | Source File |
|--------|------------------|---------|---------------|-----|--------|-----------|---------|-------------|
| Buffer | 0 | 65.2 | 0.3 | 0.987 | AUC | High reliability | ✅ | data.zip |
| Ligand_1µM | 1.0E-06 | 68.5 | 0.2 | 0.992 | AUC | High reliability | ✅ | data.zip |

**If no data**: Empty table with headers + note: "No Basic Analysis results. Please run analysis first."

#### Sheet 2: `Dose_Response`
**Content**: EC50 analysis results

| Temperature (°C) | EC50 (M) | EC50 Error (M) | R² | Hill Slope | QC Status | QC Flag | N Points |
|-----------------|----------|----------------|-----|------------|-----------|---------|----------|
| 25 | 5.2E-07 | 1.2E-07 | 0.985 | 1.2 | High reliability | ✅ | 8 |
| 37 | 2.1E-06 | 4.3E-07 | 0.978 | 1.1 | Acceptable | ⚠️ | 8 |

**If no data**: Empty table with headers + note: "No Dose-Response analysis run. Please navigate to Dose-Response tab and run analysis to generate EC50 data."

#### Sheet 3: `Thermodynamics`
**Content**: Van't Hoff parameters and KD extrapolations

| Parameter | Value | Unit | Error | QC Status |
|-----------|-------|------|-------|-----------|
| R² | 0.991 | - | - | ✅ High reliability |
| N Points | 8 | - | - | - |
| ΔH | -5.9 | kJ/mol | 1.2 | - |
| ΔS | 28.2 | cal/mol·K | 3.8 | - |
| KD (298K / 25°C) | 450 | nM | 85 | High confidence |
| KD (310K / 37°C) | 1200 | nM | 320 | Moderate confidence |

**If no data**: Empty table with headers + note: "No Thermodynamics analysis run. Please navigate to Thermodynamics tab and run Van't Hoff analysis to generate thermodynamic parameters."

#### Sheet 4: `Analysis_Settings`
**Content**: All user-selected parameters and default values

**Section 1: Basic Analysis Settings**
| Parameter | Value | Description |
|-----------|-------|-------------|
| Tm Method | AUC | Method used for Tm calculation |
| Baseline Method | Linear | Baseline fitting approach |
| Temperature Range | 25-95°C | Analysis temperature window |
| QC Enabled | Yes | Quality control checks active |

**Section 2: Dose-Response Settings**
| Parameter | Value | Description |
|-----------|-------|-------------|
| Fitting Method | 4-Parameter Logistic | Hill equation variant |
| Initial EC50 Guess | Auto | Starting value for optimization |
| QC Enabled | Yes | Quality control checks active |

**Section 3: Thermodynamics Settings**
| Parameter | Value | Description |
|-----------|-------|-------------|
| Unit System | Calorie | kcal/mol vs kJ/mol |
| Temperature Slices | 5 | Number of isothermal points |
| Slice Window | ±2°C | Temperature range per slice |
| QC Enabled | Yes | Quality control checks active |

**Section 4: QC Thresholds**
| QC Parameter | Threshold | Module |
|--------------|-----------|--------|
| Minimum R² (Critical) | 0.80 | Tm Analysis |
| Recommended R² | 0.95 | Tm Analysis |
| Minimum Data Points | 3 | Dose-Response |
| Van't Hoff R² (Critical) | 0.80 | Thermodynamics |

**Section 5: Export Metadata**
| Field | Value |
|-------|-------|
| Export Date | 2026-01-10 14:30:52 |
| QuantDSF Version | 0.9.0 |
| Uploaded Files | protein_20250110.zip |

### Excel Formatting

**Styling**:
- **Headers**: Bold, blue background (#4472C4), white text, freeze top row
- **QC Flags**: Conditional formatting
  - ✅ Green background (#C6EFCE)
  - ⚠️ Yellow background (#FFEB9C)
  - ❌ Red background (#FFC7CE)
- **Numbers**:
  - Concentrations: Scientific notation (e.g., `1.0E-06`)
  - Tm/Temperature: 1 decimal place (e.g., `65.2`)
  - R²: 3 decimal places (e.g., `0.987`)
  - Errors: 1 decimal place or scientific notation
- **Column Width**: Auto-fit
- **Borders**: Light gray grid lines

### PNG Figure Export

**Specifications**:
- **Resolution**: 300 DPI (publication quality)
- **Format**: PNG with transparent background (where applicable)
- **Dimensions**: Match current plot size in UI (typically 1200×800 px @ 300 DPI = 4×2.67 inches)
- **Naming Convention**: `[Tab_Name]_[Number].png`

**Figure Mapping**:

| Tab | Figure ID | Export Filename | Condition |
|-----|-----------|----------------|-----------|
| Basic Analysis | `melting-curves-plot` | `Basic_Analysis_1.png` | Always (if analysis run) |
| Basic Analysis | `tm-distribution-plot` | `Basic_Analysis_2.png` | If plot exists |
| Dose Response | `ec50-temp-plot` | `Dose_Response_1.png` | If analysis run |
| Dose Response | `dose-curves-grid` | `Dose_Response_2.png` | If plot exists |
| Thermodynamics | `vanthoff-plot` | `Thermodynamics_1.png` | If analysis run |
| Thermodynamics | `vh-overlay-plot` | `Thermodynamics_2.png` | If plot exists |
| Thermodynamics | `isothermal-panels-plot` | `Thermodynamics_3.png` | If plot exists |

**Empty Content Handling**:
- **Tables**: Export empty table with headers + informational note
- **Figures**: Skip completely (do not generate empty PNG files)

1. **Summary** - Project metadata and QC overview
   - Project name, upload date, file list
   - Overall QC status (% pass/warn/fail)
   - Software version, analysis settings

2. **Tm_Results** - Basic analysis table
   - All columns from CSV format
   - Conditional formatting (green/yellow/red by QC)
   - Freeze panes on header row

3. **Dose_Response** - EC50 analysis table
   - Temperature series with EC50 values
   - QC metrics highlighted

4. **VanHoff_Thermodynamics** - Thermodynamic parameters
   - Parameter table with units
   - KD extrapolations with confidence intervals

5. **Raw_Data** (Optional) - Raw melting curves
   - Temperature column + fluorescence for each capillary
   - Large datasets may skip this

6. **QC_Report** - Detailed QC metrics
   - Per-sample QC checklist
   - Flagged issues with recommendations

**Formatting**:
- Bold headers with background color
- Number formats: `0.00E+00` for concentrations, `0.00` for Tm
- Freeze top row
- Auto-fit column widths
- Color-coded QC status

### 3. Figure Export

**Purpose**: High-resolution publication-ready images

#### Supported Formats

- **PNG**: 300 DPI, transparent background option
- **SVG**: Vector format for editing in Illustrator/Inkscape
- **PDF**: Multi-page report option

#### Export Options

**Per-Figure Export**:
- Each plot has a "📷 Download Figure" button
- Dropdown: PNG (300dpi) / SVG / PDF
- Default filename: `[PlotType]_[Timestamp].png`

**Batch Figure Export**:
- "Download All Figures" button at bottom of each page
- Creates ZIP: `Figures_[Module]_[Timestamp].zip`
- Contains all plots from current analysis

### 4. QC Report Export

**Purpose**: Standalone QC documentation for record-keeping

**Format**: PDF or Excel

**Content**:
- Executive summary (pass/fail counts)
- Per-sample QC checklist with criteria
- Flagged issues with explanations
- Recommendations for failed samples
- Settings snapshot (method, thresholds)

---

## 🎨 User Interface Design

### Export Button Location

**Position**: Left sidebar, below "Run Analysis" button

```
┌─────────────────────────────────┐
│  Sidebar (Left Panel)           │
├─────────────────────────────────┤
│                                 │
│  [Upload Data]                  │
│                                 │
│  ⚙️ Settings                    │
│  ├─ Tm Method: AUC              │
│  ├─ Temperature Range: ...      │
│  └─ ...                         │
│                                 │
│  ┌───────────────────────────┐  │
│  │  ▶️ Run Analysis          │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │  📊 Export Results        │  │  ← NEW BUTTON
│  └───────────────────────────┘  │
│                                 │
└─────────────────────────────────┘
```

### Button Specifications

**Visual Design**:
- **Size**: Large, same width as "Run Analysis"
- **Color**:
  - Enabled: Green (`#28a745`) - indicates "ready to download"
  - Disabled: Gray (`#6c757d`) - before analysis is run
- **Icon**: 📊 (bar chart) or 📦 (package)
- **Text**: "Export Results"
- **Loading State**: Spinner + "Generating export package..."

**Behavior**:
- **Disabled State**: Gray, cursor not-allowed
  - Tooltip: "Please run Basic Analysis first to enable export"
- **Enabled State**: Green, cursor pointer
  - Tooltip: "Download all results as ZIP (Excel + PNG figures)"
- **Click Action**:
  1. Button changes to loading state (spinner + "Generating...")
  2. System generates ZIP in background (may take 2-10 seconds)
  3. Browser downloads ZIP file
  4. Button returns to enabled state
  5. Success toast notification: "✅ Export complete: QuantDSF_Export_[timestamp].zip"

**Enable Condition**:
- Minimum requirement: Basic Analysis has been run successfully
- Dose-Response and Thermodynamics can be missing (empty sheets will be created)

---

## 🔧 Implementation Plan

### Task Breakdown

#### Task 1: Core Export Infrastructure
**Priority**: HIGH
**Estimated Time**: 3-4 hours

**Subtasks**:
1. Create `core/io/exporters/complete_exporter.py`
   - `create_complete_export_package()` - main orchestrator
   - Returns ZIP file bytes
2. Create `core/io/exporters/figure_exporter.py`
   - `export_plotly_to_png(fig, dpi=300)` - uses `kaleido` library
   - Returns PNG bytes
3. Update `core/io/exporters/excel_exporter.py`
   - Rewrite to create 4-sheet workbook (Basic/Dose/Thermo/Settings)
   - Add empty sheet handling with informational notes
   - Add Excel formatting (colors, freeze panes, number formats)
4. Remove CSV exporter references (not needed)
   - Remove from `__init__.py`

**Dependencies**:
- `kaleido` for Plotly PNG export (may need to install)
- `openpyxl` for Excel formatting (already used)

#### Task 2: Data Aggregation Layer
**Priority**: HIGH
**Estimated Time**: 2-3 hours

**Subtasks**:
1. Create `core/io/exporters/data_aggregator.py`
   - `aggregate_basic_analysis_data()` - extract Tm results from session
   - `aggregate_dose_response_data()` - extract EC50 results
   - `aggregate_thermodynamics_data()` - extract Van't Hoff results
   - `aggregate_analysis_settings()` - extract all settings from UI state
2. Define data transfer objects (DTOs) for export
   - May use existing Pydantic models or create export-specific dicts

**Challenge**: Need to access session state/cache from callback
- Review how data is currently stored (dcc.Store? callback outputs?)

#### Task 3: Export Callback Implementation
**Priority**: HIGH
**Estimated Time**: 2-3 hours

**Subtasks**:
1. Update `app/callbacks/export_callbacks.py`
   - Create main export callback with inputs from all analysis results
   - Use `dcc.Store` components to cache analysis results
   - Call `create_complete_export_package()`
   - Return `dcc.send_bytes()` for ZIP download
2. Add enabling logic
   - Callback disables export button until Basic Analysis completes
   - Use `prevent_initial_call=True`

**Inputs** (State/Input):
- Basic Analysis results (from `dcc.Store` or callback chain)
- Dose-Response results (may be None)
- Thermodynamics results (may be None)
- All settings (from sidebar components)
- Figure objects (from graph components)

**Outputs**:
- `download-export-zip` component data
- Button loading state

#### Task 4: UI Integration
**Priority**: HIGH
**Estimated Time**: 2 hours

**Subtasks**:
1. Add export button to `app/components/sidebar.py`
   - Position below "Run Analysis" button
   - Add `dcc.Download(id='download-export-zip')`
   - Initial state: disabled
2. Add `dcc.Store` components for caching results (if not already exists)
   - `basic-analysis-store` (JSON)
   - `dose-response-store` (JSON)
   - `thermodynamics-store` (JSON)
3. Update analysis callbacks to populate stores
   - Modify existing callbacks to write to `dcc.Store`
4. Register export callback in `app/app.py`

#### Task 5: Figure ID Mapping
**Priority**: HIGH
**Estimated Time**: 1 hour

**Subtasks**:
1. Audit all graph component IDs across three tabs
   - Verify IDs match design doc (e.g., `melting-curves-plot`)
2. Create figure ID → filename mapping dict in `figure_exporter.py`
3. Add conditional logic to skip missing figures

#### Task 6: Testing & Debugging
**Priority**: HIGH
**Estimated Time**: 2-3 hours

**Test Cases**:
1. Export with only Basic Analysis run
   - Should have populated Basic sheet + empty Dose/Thermo sheets
   - Should include Basic figures only
2. Export with all three analyses run
   - All sheets populated
   - All figures included
3. Export with no analysis run
   - Button should be disabled
4. Large dataset (100+ capillaries)
   - Verify ZIP generation doesn't timeout
   - Check file size (should be <50 MB typically)

**Debugging Tools**:
- Print statements in exporter functions
- Dash debug mode for callback inspection
- Manual ZIP extraction to verify contents

#### Task 7: Polish & Documentation
**Priority**: MEDIUM
**Estimated Time**: 1-2 hours

**Subtasks**:
1. Add toast notifications
   - Success: "Export complete: [filename]"
   - Error: "Export failed: [reason]"
2. Add loading spinner to button
3. Update user guide with export instructions
4. Add docstrings to all export functions

### Implementation Order

**Sprint 1** (Core Functionality):
1. Task 1: Core Export Infrastructure
2. Task 2: Data Aggregation Layer
3. Task 5: Figure ID Mapping

**Sprint 2** (Integration):
4. Task 3: Export Callback Implementation
5. Task 4: UI Integration

**Sprint 3** (Validation):
6. Task 6: Testing & Debugging
7. Task 7: Polish & Documentation

**Total Estimated Time**: 13-18 hours (approximately 2-3 working days)

---

## 📊 Data Model Mapping

### Current Data Models → Export Fields

**TmResult → Tm CSV/Excel**:
```python
TmResult:
  .tm → Tm_degC
  .tm_error → Tm_Error_degC
  .r_squared → R_squared
  .method → Method
  .quality_flag → QC_Flag

CapillaryData:
  .name → Sample
  .concentration → Concentration_M
  .source_file → Source_File
```

**EC50 Analysis → Dose-Response CSV/Excel**:
```python
# Need to identify the data structure for EC50 results
# TODO: Review dose_response_callbacks.py for result format
```

**VanHoffResult → Thermodynamics CSV/Excel**:
```python
VanHoffResult:
  .r_squared → R_squared
  .n_points → N_points
  .thermodynamics.delta_h → Delta_H (with unit conversion)
  .thermodynamics.delta_s → Delta_S (with unit conversion)
  .kd_298k → KD_298K
  .kd_310k → KD_310K
  .reliability_298k.level → KD_298K_Reliability
```

---

## 🚨 Technical Considerations

### 1. Data Storage & State Management

**Challenge**: Export needs access to results from all three tabs, but Dash callbacks are stateless.

**Solution**: Use `dcc.Store` components to cache analysis results
- `basic-analysis-store` - stores Tm results + metadata
- `dose-response-store` - stores EC50 results
- `thermodynamics-store` - stores Van't Hoff results
- `analysis-settings-store` - stores all user settings

**Storage Format**: JSON-serialized dictionaries
- Pydantic models will be converted to dict via `.dict()`
- Figure objects are NOT stored (accessed directly from graph components)

**Size Estimation**:
- Basic Analysis: ~50-100 KB (100 capillaries)
- Dose-Response: ~10-20 KB
- Thermodynamics: ~5-10 KB
- **Total**: <200 KB (well within browser limits)

### 2. File Size Estimation

**Typical Export Package**:
- Excel workbook: 50-500 KB (depends on number of capillaries)
- PNG figures (300 DPI): 200-500 KB each × 7 figures max = 1.4-3.5 MB
- **Total ZIP**: 2-4 MB (typical), up to 10 MB (large datasets)

**Browser Limits**: 100+ MB (no issue for our use case)

**No mitigation needed** - our exports will be well within safe limits

### 3. Filename Conventions

**ZIP Archive**: `QuantDSF_Export_YYYYMMDD_HHMMSS.zip`
- Example: `QuantDSF_Export_20260110_143052.zip`

**Excel Workbook** (inside ZIP): `QuantDSF_Results.xlsx`
- Simple, consistent name

**Figures** (inside ZIP): `[Tab_Name]_[Number].png`
- Examples: `Basic_Analysis_1.png`, `Thermodynamics_2.png`

**No user customization** - keeps implementation simple

### 4. Error Handling

**Scenarios & Mitigations**:

| Error | Cause | UI Feedback | Resolution |
|-------|-------|-------------|------------|
| Export disabled | No Basic Analysis run | Gray button + tooltip | User runs analysis first |
| Export fails | Exception in exporter | Error toast notification | Retry button or refresh page |
| Missing figures | Graph not rendered | Skip silently | No error (expected behavior) |
| Kaleido timeout | PNG export slow | Loading spinner | Increase timeout to 30s |

**Error Toast Example**:
```
❌ Export failed: Unable to generate Excel workbook
Please try again or contact support if issue persists.
[Retry Button]
```

### 5. Plotly Figure Export (Kaleido)

**Library**: `kaleido` - Plotly's static image export engine

**Installation**:
```bash
pip install kaleido
```

**Usage**:
```python
import plotly.graph_objects as go
fig.write_image("output.png", width=1200, height=800, scale=2.5)  # 300 DPI
```

**Potential Issue**: Kaleido requires system dependencies
- Windows: Should work out of box
- Linux/Mac: May need Chrome/Chromium installed
- **Mitigation**: Include in requirements.txt and test during setup

---

## ✅ Finalized Design Decisions

All open questions have been resolved based on user feedback:

1. **Export Scope**: All tabs (Basic/Dose/Thermo) in one package
   - Empty sheets with notes if analysis not run

2. **Format**: Excel workbook + PNG figures, packaged in ZIP
   - No CSV export (scientists prefer Excel)

3. **UI**: Single large "Export Results" button in sidebar
   - No per-figure download buttons (simplicity)

4. **Units**: Export respects current UI settings (kcal vs kJ)
   - Units included in column headers for clarity

5. **Filenames**: Auto-generated with timestamp
   - No customization option (keeps it simple)

6. **Empty Content**:
   - Tables: Empty with informational note
   - Figures: Skip completely (don't generate empty PNGs)

---

## 🎯 Success Criteria

**Definition of Done**:
- [ ] "Export Results" button appears in sidebar below "Run Analysis"
- [ ] Button is disabled (gray) when no analysis has been run
- [ ] Button becomes enabled (green) after Basic Analysis completes
- [ ] Clicking button generates ZIP file containing:
  - [ ] Excel workbook with 4 sheets (Basic/Dose/Thermo/Settings)
  - [ ] All visible PNG figures (300 DPI)
- [ ] Empty analysis tabs show placeholder tables with notes
- [ ] Missing figures are skipped (not exported as empty files)
- [ ] ZIP downloads automatically to user's Downloads folder
- [ ] Success toast notification appears after export
- [ ] Export works with only Basic Analysis run
- [ ] Export works with all three analyses run
- [ ] Excel workbook is properly formatted (colors, freeze panes, number formats)
- [ ] Exported data matches what's shown in UI (same units, same values)
- [ ] Analysis settings are correctly captured in Settings sheet
- [ ] File size is reasonable (<10 MB for typical datasets)
- [ ] Export completes within 10 seconds for typical datasets

**Testing Checklist**:
- [ ] Test with only Basic Analysis
- [ ] Test with Basic + Dose-Response
- [ ] Test with all three analyses
- [ ] Test with large dataset (100+ capillaries)
- [ ] Verify Excel opens correctly in Microsoft Excel
- [ ] Verify Excel opens correctly in Google Sheets
- [ ] Verify PNG figures are high quality (300 DPI)
- [ ] Verify QC flags appear correctly in Excel (colors)

---

## 📚 References

**Existing Code**:
- [core/io/exporters/excel_exporter.py](../core/io/exporters/excel_exporter.py) - Excel export logic
- [app/callbacks/export_callbacks.py](../app/callbacks/export_callbacks.py) - Export callbacks
- [app/layouts/thermodynamic.py](../app/layouts/thermodynamic.py#L212-L222) - Export UI section

**Data Models**:
- [core/models/analysis.py](../core/models/analysis.py) - `TmResult`
- [core/models/thermodynamic.py](../core/models/thermodynamic.py) - `VanHoffResult`
- [core/qc/](../core/qc/) - QC metrics models

**Dependencies**:
- `pandas` - DataFrame manipulation
- `openpyxl` - Excel file generation
- `plotly` - Figure export utilities (kaleido for static images)
- `dash` - `dcc.Download` component

---

## 📅 Dependencies & Prerequisites

**Required Libraries**:
- `openpyxl` - Excel file generation (already installed)
- `kaleido` - Plotly PNG export (needs installation)
- `zipfile` - ZIP packaging (Python built-in)

**Installation**:
```bash
pip install kaleido
```

**Code Dependencies**:
- Existing Pydantic models (`TmResult`, `VanHoffResult`, etc.)
- Existing graph components with stable IDs
- QC metrics integration (already complete)

---

## 🔄 Next Steps

**Immediate Actions**:
1. ✅ Design document reviewed and approved by user
2. 🔨 Install `kaleido` dependency
3. 🔨 Audit existing graph IDs (verify they match design doc)
4. 🔨 Begin Sprint 1: Core Export Infrastructure
   - Create `complete_exporter.py`
   - Create `figure_exporter.py`
   - Rewrite `excel_exporter.py`

**Implementation Sequence**:
- **Sprint 1** (Days 1-2): Core infrastructure + figure mapping
- **Sprint 2** (Days 2-3): Callback integration + UI button
- **Sprint 3** (Days 3-4): Testing + polish + documentation

**Total Timeline**: 2-3 working days

---

**Document Status**: ✅ Approved - Ready for Implementation
**Next Action**: Install kaleido and start Sprint 1
