# QuantDSF UI Specification

**Version**: 1.0  
**Date**: 2026-01-22  
**Status**: Live  

---

## 1. Overview

The QuantDSF User Interface is built using **Dash** (Python framework for web apps) and **Dash Bootstrap Components (DBC)**. It features a responsive, single-page application layout with a persistent sidebar and tabbed content area.

### 1.1 Technology Stack
- **Framework**: Dash 2.x
- **Component Library**: Dash Bootstrap Components (Bootstrap 5)
- **Icons**: FontAwesome 5 (Free)
- **Plotting**: Plotly Graph Objects
- **Styling**: Standard Bootstrap utility classes (e.g., `shadow-sm`, `bg-primary`) + minimal inline styles.

---

## 2. Layout Structure

The application uses an optimized dashboard layout designed for maximum data visibility:

```
┌─────────────────────────────────────────────────────────────┐
│    Navbar (Branding + Title + Description + Links)          │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│              │  [ Tab 1 ] [ Tab 2 ] [ Tab 3 ]               │
│              │                                              │
│   Sidebar    │  ┌────────────────────────────────────────┐  │
│   (Fixed)    │  │  Table Area (Top 1/3, Scrollable)      │  │
│              │  │                                        │  │
│              │  └────────────────────────────────────────┘  │
│              │  ┌────────────────────────────────────────┐  │
│              │  │                                        │  │
│              │  │  Plot Area (Bottom 2/3, Adaptive)      │  │
│              │  │                                        │  │
│              │  └────────────────────────────────────────┘  │
│              │                                              │
├──────────────┴──────────────────────────────────────────────┤
│                       Footer (Bottom)                       │
└─────────────────────────────────────────────────────────────┘
```

- **Navbar**: Hosts the application title ("nanoDSF Analysis Platform") and description to save vertical space.
- **Sidebar**: Sticky (fixed position), contains global controls.
- **Content Area**: Split view layout (1:2 ratio):
    - **Table Area (Top)**: Scrollable container for data tables.
    - **Plot Area (Bottom)**: Flexible container for visualization.

---

## 3. Component Specifications

### 3.1 Navbar (Header)
**Style**: `dbc.Navbar` (Dark theme).
**Content**:
- **Brand**: "QuantDSF v2" (Left).
- **Title**: "nanoDSF Analysis Platform" (Center/Left).
- **Description**: "High-throughput thermal stability..." (Small text).
- **Links**: History, Documentation, GitHub (Right).

### 3.2 Sidebar (Control Panel)
**Location**: Left column (`md=3`), sticky top (`top: 20px`).
**Style**: `dbc.Card` with `shadow-sm`.

| Section | Components | Description |
|---------|------------|-------------|
| **Header** | `CardHeader` | "Analysis Settings" title. Bg: Primary Blue. |
| **Data Upload** | `dcc.Upload` | Drag & drop zone. Dashed border. Supports multiple files. |
| **Method** | `dbc.RadioItems` | Selects Tm calc method: AUC (default), Boltzmann, Derivative. |
| **Channel** | `dbc.Select` | Selects fluorescence channel: Ratio (default), 330nm, 350nm. |
| **Thermodynamics** | `dbc.Accordion` | Collapsible. Units (kcal/kJ), Fitting params (Slice step, R² thresholds). |
| **Advanced** | `dbc.Accordion` | Collapsible. First Derivative smoothing options. |
| **Actions** | `dbc.Button` | "Run Analysis" (Primary Blue), "Export PDF Report" (Outline Success Green). |

### 3.3 Content Area Layout (Split View)
**Structure**: Vertical split with ratio approx 1:2 (Table:Plot).

#### **A. Table Area (Top)**
- **Height**: ~35vh (adjustable or scrollable).
- **Behavior**: `overflow-y: auto`. Headers stick to top.
- **Content**: Summary tables (Tm Results, EC50 parameters).

#### **B. Plot Area (Bottom)**
- **Height**: ~60vh (adaptive fill).
- **Behavior**: Charts resize to fill available space.
- **Content**: Interactive Plotly graphs (Melting Curves, Van't Hoff plots).
- **Tabs**: If multiple plots are needed, use tabs *within* the plot area to switch.

### 3.4 Basic Analysis Tab
**ID**: `tab-basic`
**Layout**: Follows Split View.

- **Table Area**: `Results Table` (Scrollable).
- **Plot Area**:
    - **Tab 1**: Melting Curves.
    - **Tab 2**: Tm Distribution.
    - **Tab 3**: First Derivative (Conditional).

### 3.5 Thermodynamic Analysis Tab
**ID**: `tab-thermo`
**Layout**: Sequential workflow adapted to Split View.

- **Table Area**: Results metrics (ΔH, ΔS cards) and summary tables.
- **Plot Area**:
    - **Tab 1**: Van't Hoff Plot.
    - **Tab 2**: Overlay Analysis.
    - **Tab 3**: Isothermal Panels.

### 3.6 Dose-Response Tab
**ID**: `tab-dose`
**Layout**: Split View.

- **Table Area**: EC50 Results Table.
- **Plot Area**: Dose-Response Curves.

---

## 4. Visual Style & Theme

### 4.1 Color Palette (Bootstrap Standard)
- **Primary**: `#0d6efd` (Blue) - Headers, Main Buttons, Active States.
- **Success**: `#198754` (Green) - Valid Status, Export Actions.
- **Warning**: `#ffc107` (Yellow) - Alerts, Cautions.
- **Danger**: `#dc3545` (Red) - Error States, Failed QC.
- **Light/White**: Backgrounds.

### 4.2 Typography
- **Font Family**: System Default (San Francisco on Mac, Segoe UI on Windows, Roboto on Android).
- **Headings**: Standard Bootstrap weight and sizing.
- **Icons**: FontAwesome solid style (`fas`).

---

## 5. User Interaction Guidelines

- **Feedback**: All long-running operations (Analysis, Export) must show a loading spinner or progress indicator.
- **Validation**: Inputs (temperature ranges) use `dbc.Input(type="number")` with min/max/step constraints.
- **Empty States**: Graphs initialize with an empty placeholder figure containing instruction text ("Upload data and run analysis").

## 6. Export Interface

- **Button**: Located at the bottom of the sidebar.
- **Label**: "Export PDF Report".
- **Visual**: Outlined Green button with PDF icon.
- **Behavior**: Triggers a download of a generated PDF file. Button enters loading state during generation.
