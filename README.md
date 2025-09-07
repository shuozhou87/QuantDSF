# nanoDSF Analysis Tool

A Streamlit-based application for analyzing nanoDSF (nano Differential Scanning Fluorimetry) data, enabling robust calculation of melting temperatures (Tm), EC₅₀ values, and ΔTm for screening campaigns.

## Overview

This tool processes raw nanoDSF data exported from Prometheus instruments (in ZIP archives containing CSV files). It offers several analysis methods and advanced features to handle complex protein unfolding behaviors, including multi-peak detection and Gaussian deconvolution for overlapping transitions. The user interface allows for flexible parameter adjustments and provides detailed visualizations of raw data, smoothed curves, derivatives, and fitted models.

**🆕 Latest Update (2025-05-28)**: Major improvements for high-resolution data handling, enhanced window size flexibility, and critical bug fixes for AUC method and curve alignment issues.

## Core Features

*   **Tm Calculation Methods**:
    *   **First Derivative**: Standard method with Savitzky-Golay smoothing and enhanced peak detection.
    *   **Two-state Boltzmann**: Fitting to a two-state unfolding model (excellent for noisy data).
    *   **AUC (Area Under Curve)**: Alternative derivative-based method for transition detection.
        *   **Method**: Calculates area under the absolute derivative curve to find the 50% transition point
        *   **Scientific Basis**: Uses the rate of fluorescence change (derivative) and finds the midpoint of total transition activity
        *   **Advantages**: Less sensitive to noise than peak detection, provides robust transition midpoint calculation
*   **Advanced Peak Analysis**:
    *   **Multi-peak Detection**: Identifies multiple transitions in a single capillary, useful for complex unfolding or ligand-induced stability changes.
    *   **Curve Interpolation**: Uses cubic interpolation for smoother curves, aiding in the detection of subtle transitions and shoulder peaks.
    *   **Gaussian Deconvolution**:
        *   Automatically fits multiple Gaussian peaks to the derivative curve to resolve overlapping transitions.
        *   **Recommended for high-resolution or noisy data** - handles noise without peak position shifting.
        *   Works in both **single-peak and multi-peak modes**.
        *   Provides improved Tm determination and **more accurate peak shape fitting (amplitude, width/sigma)**.
        *   Visualizes individual Gaussian components.
    *   **Polynomial Peak Refinement**: Fine-tunes peak positions using local polynomial fitting.
*   **Flexible Smoothing Controls**:
    *   **Savitzky-Golay window sizes up to 99** with progressive warnings about peak shifting risks.
    *   **Polynomial order selection** (1-3) for balancing smoothness vs. position accuracy.
    *   **Method-specific recommendations** to guide optimal parameter selection.
*   **Automated Helper Functions**:
    *   **Automatic Channel Recommendation**: Suggests the best data channel (350/330nm Ratio, 350nm, or 330nm) based on Signal-to-Noise Ratio (SNR) analysis of a representative capillary.
    *   **Automatic Experiment Type Detection**: Determines if the uploaded dataset is for 'dose-response' (for EC₅₀) or 'screening' (for ΔTm) based on file naming conventions.
*   **Screening & Dose-Response Analysis**:
    *   **ΔTm Screening**: Calculates and visualizes ΔTm values for samples against a user-selected control, useful for hit identification.
    *   **EC₅₀ Analysis**: Calculates EC₅₀ values from dose-response data using a 4-parameter logistic (4PL) fit (Hill equation).
*   **User Interface & Visualization**:
    *   Interactive adjustment of analysis parameters with real-time feedback and warnings.
    *   **Enhanced warning system** for peak shifting risks with window size selection.
    *   Detailed per-capillary plots showing raw data, smoothed fluorescence, derivative curves, and fitted models.
    *   Customizable summary table for results, allowing users to select displayed columns.
    *   Global Debug Output Area for troubleshooting and detailed logging when debug mode is enabled.
*   **Data Handling**:
    *   Input: ZIP archives containing raw CSV files from nanoDSF experiments.
    *   **Robust handling of high-resolution data** with appropriate method recommendations.
    *   Output: Display of results tables and plots directly in the Streamlit application.

## Recommendations for Different Data Types

### High-Resolution or Noisy Data
- **Primary Recommendation**: Use **Two-State Boltzmann** method (fits overall curve shape, immune to noise)
- **Alternative**: Use **Gaussian Deconvolution** (handles noise without peak position errors)
- **Avoid**: Large window sizes (>35) with Find Peaks method due to peak shifting

### Standard Data
- **First Derivative with Find Peaks**: Use window sizes 15-35 for best balance
- **Gaussian Deconvolution**: Excellent for any data type, especially overlapping peaks
- **Polynomial Refinement**: Enables when precise peak positioning is critical

### Multi-Peak/Complex Unfolding
- **Enable Multi-Peak Detection** with Gaussian Deconvolution
- Use **curve interpolation** to detect subtle shoulder peaks
- Consider **Two-State Boltzmann** for primary transition identification

## How to Use

1.  **Prepare your data**:
    *   Export raw data from your nanoDSF instrument.
    *   Ensure data for each experiment is contained within a single ZIP archive.
    *   For automatic experiment type detection:
        *   **Dose-response data**: Include varying concentrations in filenames
        *   **Screening data**: Use consistent naming patterns
2.  **Run the application**:
    ```bash
    streamlit run main.py
    ```
3.  **Upload your ZIP file** using the file uploader in the application.
4.  **Adjust Analysis Settings in the Sidebar**:
    *   **Tm calculation method**: Choose based on your data characteristics (see recommendations above)
    *   **Data channel**: Select or use automatic recommendation
    *   **Window length**: Start with default (25), increase cautiously with awareness of trade-offs
    *   **Multi-peak detection**: Enable for complex unfolding patterns
    *   **Gaussian deconvolution**: Recommended for noisy or high-resolution data
    *   **Table Display Settings**: Customize results display
5.  **Interpret Results**:
    *   View the summary table with quality metrics and flags
    *   Pay attention to warnings about peak shifting or data quality
    *   Expand individual capillary sections for detailed analysis
    *   Perform EC₅₀ or ΔTm analysis as needed

## Recent Highlights (2025-05-28 Update)

### 🔧 Critical Bug Fixes
*   **AUC Method Reprocessing**: Fixed issue where AUC parameter changes weren't triggering data reanalysis
*   **Curve Alignment**: Resolved severe curve misalignment issues caused by aggressive edge trimming
*   **Variable Definition**: Fixed `window_length` undefined error for AUC method

### 🚀 Major Improvements
*   **Enhanced Window Size Flexibility**: Increased limits to 99 with progressive warning system
*   **Method-Specific Guidance**: Tailored recommendations for each analysis method
*   **Polynomial Order Control**: Added user control over Savitzky-Golay polynomial order
*   **High-Resolution Data Handling**: Improved recommendations and method selection for high-resolution datasets

### 🎯 Key Technical Insights
*   **Peak Shifting Understanding**: Large Savitzky-Golay windows inherently cause peak shifts (mathematical property)
*   **Alternative Approaches**: Gaussian deconvolution and TSB methods handle noisy data without position errors
*   **Simplified Processing**: Removed complex preprocessing that introduced artifacts

### 📊 User Experience Enhancements
*   **Progressive Warnings**: Clear guidance about window size effects and method limitations
*   **Method Recommendations**: Data-type specific suggestions for optimal analysis
*   **Improved Reliability**: Simplified approaches that are more robust and transparent

## Project Structure

```
.
├── main.py                 # Main Streamlit application script
├── analysis/               # Core analysis modules
│   ├── tm_analysis.py      # Primary Tm calculation routines
│   ├── calc/               # Specialized calculation modules
│   │   ├── derivative_analysis.py  # Enhanced derivative method implementation
│   │   ├── signal_processing.py   # Signal processing utilities
│   │   ├── peak_refinement.py     # Advanced peak detection and refinement
│   │   └── tm_calc_original.py    # Gaussian deconvolution implementation
│   ├── ec50_analysis.py    # EC₅₀ fitting functions
│   └── screening.py        # ΔTm calculation functions
├── utils/                  # Utility functions
│   ├── io_utils.py         # Data input/output and preprocessing
│   └── parser.py           # Filename and concentration parsing
├── visualization/          # Plotting and display functions
│   └── plots.py            # Enhanced plotting with method-specific visualizations
├── change.log              # Comprehensive change tracking
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  Install dependencies (preferably in a virtual environment):
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the Streamlit application:
```bash
streamlit run main.py
```
Navigate to the URL provided by Streamlit in your web browser.

## Troubleshooting

### Common Issues and Solutions

1. **Peak Shifting with Large Windows**: 
   - Use smaller window sizes (≤35) for Find Peaks method
   - Switch to Gaussian Deconvolution for noisy data

2. **Poor Fits with Noisy Data**:
   - Try Two-State Boltzmann method
   - Enable Gaussian Deconvolution
   - Consider curve interpolation

3. **Missing Secondary Peaks**:
   - Enable multi-peak detection
   - Use Gaussian Deconvolution
   - Adjust window length (21-25 often works well)

4. **Curve Alignment Issues**:
   - Check that all methods use standard smoothing only
   - Avoid aggressive preprocessing options

For detailed troubleshooting, enable Debug Mode in the sidebar for comprehensive logging.

---

**Current Status**: Fully operational with enhanced high-resolution data support and improved user guidance.
**Recommended Port**: 8506 (if others are in use)

*Last Updated: 2025-05-28* 