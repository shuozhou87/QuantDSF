# QuantDSF Input/Output Specification

**Version**: 2.0
**Last Updated**: 2026-01-09
**Status**: Finalized for Production

---

## Table of Contents

1. [Input Specifications](#input-specifications)
2. [Output Specifications](#output-specifications)
3. [Error Messages](#error-messages)
4. [Data Quality Standards](#data-quality-standards)

---

## Input Specifications

### 1.1 Supported File Formats

QuantDSF accepts ZIP archives containing nanoDSF data from two instrument types:

#### **Primary Format: ZIP Archive**
- **Extension**: `.zip`
- **Required**: Yes
- **Content**: One or more data files from supported instruments

#### **Supported Instruments**

##### **Prometheus NT.Panta (NT.48)**
- **Manufacturer**: NanoTemper Technologies
- **File Type**: Tab-separated CSV (`.csv`)
- **File Naming**:
  - `*_raw.csv` (raw data)
  - `*_processed.csv` (processed data, default preference)
- **Required Columns**:
  - Column 1: `T[°C]` (temperature in Celsius)
  - Column 2: Fluorescence signal (ratio, 330nm, or 350nm)
- **Separator**: Tab (`\t`)
- **Encoding**: UTF-8

**Example File Structure**:
```
Sample1_Ratio_0.1uM_processed.csv:
T[°C]	Ratio
20.0	1.234
21.0	1.245
...
```

##### **Tycho NT.6**
- **Manufacturer**: NanoTemper Technologies
- **File Types**:
  - CSV (`.csv`, `.txt`) - single capillary
  - Excel (`.xlsx`) - multi-capillary batch export

**CSV Format**:
- **Separators**: Auto-detect (comma, tab, semicolon)
- **Required Columns**:
  - Temperature column: containing keywords like `temp`, `temperature`, `T[°C]`, `°C`
  - Fluorescence column: containing keywords like `fluor`, `signal`, `intensity`, `ratio`, `channel`
- **Minimum Data Points**: 10

**Excel Format**:
- **Required Sheets**:
  - `Results`: Contains capillary labels and metadata
  - `Profiles_raw`: Contains temperature and fluorescence data
  - `Profiles_smoothed`: Smoothed data (not used by QuantDSF)
  - `Profiles_derivative`: Derivative data (not used by QuantDSF)
- **Data Channels**:
  - **350/330 nm ratio** (columns 2-7): Default for thermal stability
  - **330 nm** (columns 9-14): Tryptophan fluorescence
  - **350 nm** (columns 16-21): Tyrosine fluorescence
- **Capillaries**: Up to 6 per run

**Example Excel Structure**:
```
Results Sheet:
Row 2: Cap# | Capillary # | Sample Name | ...
Row 3:   1  |      1      | ProteinA    | ...

Profiles_raw Sheet:
Row 6: Temperature | 350/330 ratio (Cap1) | ... | 330nm (Cap1) | ...
Row 7:   20.0      |       1.234          | ... |    12.34     | ...
```

---

### 1.2 File Naming Conventions

#### **Concentration Detection**
QuantDSF automatically extracts ligand/buffer concentrations from filenames using these patterns:

**Supported Formats**:
- `10uM`, `10µM`, `10 uM` → 1.0e-5 M
- `100nM`, `100 nM` → 1.0e-7 M
- `1mM`, `1 mM` → 1.0e-3 M
- `0.1M`, `0.1 M` → 0.1 M
- Scientific notation: `1e-6M`, `1E-6 M`

**Examples**:
```
BSA_10uM_ratio_processed.csv       → 1.0e-5 M
Lysozyme_100nM_330nm_raw.csv       → 1.0e-7 M
Protein_1mM_Cap1_350nm.csv         → 1.0e-3 M
Sample_0.5uM_replicate1.csv        → 5.0e-7 M
Apo_control.csv                    → None (no concentration)
```

#### **Sample Name Cleaning**
QuantDSF automatically cleans sample names by removing:
- Redundant suffixes: `_raw`, `_processed`, `_Unfolding`, `_Ratio`, `_330nm`, `_350nm`
- Concentration strings (extracted separately)
- Extra whitespace
- Underscores replaced with spaces (user configurable)

**Example Transformations**:
```
Input:  "BSA_10uM_Ratio_processed"
Output: "BSA" (concentration stored as 1.0e-5 M)

Input:  "Lysozyme_Buffer_330nm_Unfolding_raw"
Output: "Lysozyme Buffer"

Input:  "ProteinX_0.1uM_Rep1_350/330_nm_ratio"
Output: "ProteinX Rep1" (concentration: 1.0e-7 M)
```

---

### 1.3 Data Channel Selection

Users can select which fluorescence channel to analyze:

| Channel | Description | Use Case |
|---------|-------------|----------|
| **350/330 nm Ratio** | Ratio of 350nm/330nm emission | **Default** - Most robust for thermal stability |
| **330 nm** | Tryptophan fluorescence | Proteins rich in tryptophan |
| **350 nm** | Tyrosine fluorescence | Proteins with exposed tyrosines |

**Implementation**:
- Prometheus: Determined by filename (e.g., `_Ratio.csv`, `_330nm.csv`)
- Tycho CSV: Single channel per file
- Tycho Excel: All channels extracted, user selects in UI

---

### 1.4 Data Filtering Rules

#### **Excluded Files**
QuantDSF automatically skips:
- Hidden files: `.*`, `__*`
- Documentation: `README*`, `Info*`, `Documentation*`, `Metadata*`
- Turbidity data: `*turbidity*` (not used in DSF analysis)
- Wrong channel: Files not matching selected channel

#### **Invalid Data**
Samples are rejected if:
- **Insufficient data points**: < 10 valid (T, F) pairs
- **Non-numeric data**: Temperature or fluorescence contains NaN/Inf
- **Temperature range**: T < 10°C or T > 120°C (sanity check)
- **Missing columns**: Required temperature or fluorescence column not found

---

### 1.5 Processing Preferences

#### **Raw vs. Processed Data**
- **Default**: Prefer processed data (`*_processed.csv`)
- **User Option**: "Use raw data" checkbox
  - When checked: Skip `*_processed.csv`, use `*_raw.csv` only
  - When unchecked: Skip `*_raw.csv`, use `*_processed.csv` only

**Rationale**: Prometheus software applies proprietary smoothing. Users may prefer raw data for custom analysis.

---

## Output Specifications

### 2.1 Interactive Results Table

#### **Displayed Columns**

| Column | Description | Format | Example |
|--------|-------------|--------|---------|
| **Sample** | Cleaned sample name | String | "BSA" |
| **Concentration (M)** | Ligand concentration | Scientific notation or "—" | 1.00e-5 or "—" |
| **Tm (°C)** | Melting temperature | 2 decimal places or "—" | 65.42 or "—" |
| **R²** (TSB/AUC) | Goodness of fit | 3 decimal places | 0.997 |
| **SNR** (Derivative) | Signal-to-noise ratio | 1 decimal place | 8.5 |
| **Method** | Analysis method used | Uppercase acronym | TSB, AUC, FD |
| **Status** | Quality indicator | Emoji | ✅, ⚠️, ❌ |

#### **Status Indicators**

| Status | Meaning | Criteria |
|--------|---------|----------|
| ✅ | High quality | R² ≥ 0.90 (TSB/AUC) or SNR ≥ 3.0 (FD) |
| ⚠️ | Low quality | R² < 0.90 (TSB/AUC) or SNR < 3.0 (FD) |
| ❌ | Failed | Analysis failed or Tm not found |

**Hover Tooltips**:
- ✅: No additional info
- ⚠️: "Low R²: 0.856 (threshold: 0.90)" or "Low SNR: 2.3 (threshold: 3.0)"
- ❌: "Analysis failed or Tm not found"

#### **Sorting**
Default sort order:
1. By concentration (low to high)
2. Samples without concentration at the end
3. Within same concentration: alphabetical by sample name

---

### 2.2 Interactive Plots

#### **Plot 1: Melting Curves**
- **X-axis**: Temperature (°C)
- **Y-axis**: Normalized Fluorescence (0 to 1)
- **Traces**: One per sample (color-coded)
- **Features**:
  - Hover: Shows (T, F, Sample name)
  - Legend: Clickable to show/hide traces
  - Zoom/pan enabled

#### **Plot 2: Tm Distribution**
- **Type**: Histogram + box plot overlay
- **X-axis**: Tm (°C)
- **Y-axis**: Count
- **Features**:
  - Shows distribution of Tm values
  - Box plot shows median, quartiles, outliers

#### **Plot 3: First Derivative Curves** (FD method only)
- **X-axis**: Temperature (°C)
- **Y-axis**: dF/dT (first derivative)
- **Traces**: One per sample
- **Markers**: Peak position = Tm
- **Visibility**: Only shown when First Derivative method is selected

---

### 2.3 Excel Export

#### **File Format**
- **Format**: `.xlsx` (Excel 2007+)
- **Engine**: openpyxl
- **Filename**: `QuantDSF_Results_<timestamp>.xlsx`

#### **Sheet 1: Tm Results**

| Column | Description | Type | Example |
|--------|-------------|------|---------|
| Sample | Sample name | String | "BSA" |
| Concentration (M) | Ligand concentration | Float or empty | 1.0e-5 |
| Tm (°C) | Melting temperature | Float or empty | 65.42 |
| R² / SNR | Fit quality | Float | 0.997 |
| Method | Analysis method | String | "boltzmann" |
| Status | Quality flag | String | "✅" |
| Source File | Original data file | String | "BSA_10uM_processed.csv" |

#### **Sheet 2: Van't Hoff** (if applicable)
Only included when thermodynamic analysis is performed.

| Parameter | Value |
|-----------|-------|
| R² | 0.995 |
| n_points | 8 |
| ΔH (J/mol) | -250000 |
| ΔS (J/mol/K) | -840 |
| KD at 298K (M) | 1.2e-6 |
| KD at 310K (M) | 8.3e-7 |
| Reliability 298K | HIGH |
| Reliability 310K | MEDIUM |

---

## Error Messages

### 3.1 File Upload Errors

#### **E001: Invalid File Type**
```
❌ Invalid file format
Only ZIP archives are supported.
Please upload a .zip file containing nanoDSF data.
```
**Cause**: User uploaded non-ZIP file
**Resolution**: Upload ZIP archive

#### **E002: Empty ZIP**
```
❌ Empty ZIP archive
No valid data files found in the uploaded ZIP.
Please ensure the ZIP contains CSV or Excel files from Prometheus or Tycho instruments.
```
**Cause**: ZIP contains no parseable data files
**Resolution**: Check ZIP contents

#### **E003: Unsupported Instrument**
```
❌ Unsupported instrument format
QuantDSF supports:
- Prometheus NT.Panta (CSV files with 'T[°C]' column)
- Tycho NT.6 (CSV or Excel files)

Detected file format does not match any supported instrument.
```
**Cause**: Files in ZIP are not from Prometheus or Tycho
**Resolution**: Use data from supported instruments

#### **E004: Corrupted File**
```
❌ Unable to read file: sample_data.csv
File may be corrupted or in an unsupported encoding.
Error: [specific error message]
```
**Cause**: File read/parse error
**Resolution**: Re-export data from instrument software

---

### 3.2 Data Quality Errors

#### **W001: Insufficient Data Points**
```
⚠️ Sample "ProteinX" skipped
Reason: Only 8 data points (minimum: 10)
```
**Cause**: Temperature range too narrow or sparse sampling
**Resolution**: Use wider temperature range in experiment

#### **W002: No Valid Samples**
```
❌ No valid samples found
All samples in the uploaded data were rejected due to:
- Insufficient data points (< 10)
- Missing required columns
- Invalid numeric values (NaN/Inf)

Please check your data export settings.
```
**Cause**: All samples failed validation
**Resolution**: Check instrument export settings and data quality

#### **W003: Channel Mismatch**
```
⚠️ 5 files skipped
Selected channel: 330 nm
Files contain: 350/330 nm ratio data only

Tip: Change channel selection to "350/330 nm Ratio" to analyze these files.
```
**Cause**: User selected wrong channel
**Resolution**: Change channel selector

---

### 3.3 Analysis Errors

#### **E101: Analysis Failed**
```
❌ Analysis failed for 3 samples
Failed samples:
- ProteinA: Fitting did not converge
- ProteinB: No melting transition detected
- ProteinC: Temperature range insufficient

These samples will show "❌" status in results.
```
**Cause**: TSB/AUC fitting failed or FD peak not found
**Resolution**: Check data quality, try different method

#### **E102: Thermodynamic Analysis Failed**
```
❌ Van't Hoff analysis failed
Reason: Insufficient concentration points (found: 2, required: ≥ 3)

Thermodynamic analysis requires at least 3 different ligand concentrations.
```
**Cause**: Not enough concentration series
**Resolution**: Upload data with more concentrations

#### **W101: Low Quality Fits**
```
⚠️ 4 samples have low fit quality (R² < 0.90)
These samples are marked with "⚠️" status.
Consider:
- Checking data quality
- Trying a different analysis method
- Using TSB advanced settings to adjust smoothing
```
**Cause**: Poor fit quality
**Resolution**: Adjust analysis parameters or check data

---

### 3.4 System Errors

#### **E500: Memory Error**
```
❌ Analysis failed: Insufficient memory
Your dataset is too large for available system memory.

Try:
- Reducing the number of samples
- Splitting the dataset into multiple batches
- Running on a system with more RAM
```
**Cause**: Dataset too large
**Resolution**: Reduce dataset size

#### **E501: Computation Timeout**
```
❌ Analysis timed out
The analysis is taking longer than expected.
This may indicate a problem with the data or analysis settings.

Please try:
- Reducing the number of samples
- Simplifying the analysis method
- Contacting support if the issue persists
```
**Cause**: Computation too slow
**Resolution**: Optimize dataset or report issue

---

## Data Quality Standards

### 4.1 Acceptance Criteria

#### **Minimum Requirements**
| Parameter | Threshold | Rationale |
|-----------|-----------|-----------|
| Data points | ≥ 10 | Statistical significance |
| Temperature range | ≥ 20°C | Capture full transition |
| R² (TSB/AUC) | ≥ 0.90 | Good fit quality |
| SNR (FD) | ≥ 3.0 | Clear peak detection |

#### **Quality Tiers**

**High Quality** (✅):
- R² ≥ 0.95 (TSB/AUC) or SNR ≥ 5.0 (FD)
- Clear melting transition
- Stable baselines

**Acceptable Quality** (⚠️):
- 0.80 ≤ R² < 0.95 (TSB/AUC) or 3.0 ≤ SNR < 5.0 (FD)
- Usable for screening
- May require manual verification

**Poor Quality** (❌):
- R² < 0.80 (TSB/AUC) or SNR < 3.0 (FD)
- Fitting failed
- Tm not detectable

---

### 4.2 Recommended Experimental Design

#### **For Tm Determination**
- **Temperature range**: 20-95°C (minimum)
- **Step size**: 1°C or finer
- **Channel**: 350/330 nm ratio (default)
- **Replicates**: ≥ 3 per condition

#### **For Thermodynamic Analysis (Van't Hoff)**
- **Concentration points**: ≥ 5 (recommended), ≥ 3 (minimum)
- **Concentration range**: 2-3 orders of magnitude
- **Spacing**: Log-scale (e.g., 0.1, 0.3, 1, 3, 10 µM)
- **Replicates**: ≥ 2 per concentration

#### **For Dose-Response**
- **Concentration points**: ≥ 8
- **Range**: Cover EC₅₀ ± 2 log units
- **Controls**: Include apo (0 M) and saturating ligand

---

### 4.3 Troubleshooting Guide

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Low R² (TSB) | - Noisy data<br>- Multiple transitions | - Increase smoothing<br>- Use AUC method |
| Low SNR (FD) | - Weak signal<br>- Flat melting curve | - Use TSB/AUC method<br>- Check protein stability |
| No Tm detected | - No melting transition<br>- T range too narrow | - Extend temperature range<br>- Check protein folding |
| Scattered Tm values | - Sample heterogeneity<br>- Aggregation | - Check sample prep<br>- Filter/centrifuge |
| Concentration not detected | - Non-standard naming | - Use format: `10uM`, `100nM` in filename |

---

## Appendix

### A1. Analysis Methods

#### **Two-State Boltzmann (TSB)**
- **Model**: Exponential baseline Boltzmann
- **Equation**: F(T) = (A_N·exp(α·T) + D_N) + (A_D·exp(β·T) + D_D) / (1 + exp((Tm - T)/k))
- **Parameters**: 8 (A_N, α, D_N, A_D, β, D_D, Tm, k)
- **Output**: Tm, R²
- **Best for**: Clean, single-transition data

#### **Area Under Curve (AUC)**
- **Model**: Hill equation on progress curve
- **Approach**: Integrates fluorescence vs. temperature
- **Output**: Tm (T₅₀ from Hill fit), R²
- **Best for**: Noisy data, robust screening

#### **First Derivative (FD)**
- **Algorithm**: Savitzky-Golay smoothing + numerical derivative
- **Peak detection**: Local maximum of dF/dT
- **Output**: Tm (peak position), SNR
- **Best for**: Quick screening, no fitting required

---

### A2. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-01-09 | Finalized for production deployment |
| 1.5 | 2025-12-20 | Added Tycho Excel support |
| 1.0 | 2025-11-15 | Initial specification |

---

### A3. Contact & Support

For questions or issues:
- **GitHub Issues**: [https://github.com/shuozhou87/QuantDSF/issues](https://github.com/shuozhou87/QuantDSF/issues)
- **Production Server**: http://g1200163267.win.uthscsa.edu:9051/ (UTHSCSA internal only)

---

**Document End**
