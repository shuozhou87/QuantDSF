# QuantDSF Quality Control Guide

**Version**: 2.0
**Last Updated**: 2026-01-09
**Status**: Production

---

## Table of Contents

1. [Overview](#overview)
2. [Quality Metrics](#quality-metrics)
3. [Quality Assessment Criteria](#quality-assessment-criteria)
4. [Quality Flags and Interpretation](#quality-flags-and-interpretation)
5. [Method-Specific Quality Control](#method-specific-quality-control)
6. [Experimental Design Guidelines](#experimental-design-guidelines)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Best Practices](#best-practices)

---

## Overview

QuantDSF implements comprehensive quality control (QC) mechanisms to ensure reliable thermal stability analysis. The QC system evaluates multiple parameters and provides clear visual indicators to help users identify high-quality data and flag problematic samples.

### Design Philosophy

1. **Automated Assessment**: All quality metrics are calculated automatically
2. **Clear Visual Indicators**: Three-tier system (✅ ⚠️ ❌) for immediate interpretation
3. **Transparent Reporting**: Users can inspect all quality parameters
4. **Method-Specific**: Different QC criteria for TSB, AUC, and FD methods

---

## Quality Metrics

### 2.1 Universal Metrics (All Methods)

#### **Data Completeness**

| Metric | Minimum Threshold | Description |
|--------|------------------|-------------|
| **Valid Data Points** | ≥ 10 | Number of (T, F) pairs with no NaN/Inf |
| **Temperature Range** | ≥ 20°C | Span from T_min to T_max |
| **Temperature Coverage** | 20-95°C (recommended) | Capture full protein unfolding |

**Why it matters**:
- < 10 points: Insufficient for statistical fitting
- Narrow range: May miss Tm if outside measurement window
- Sparse sampling: Poor resolution of melting transition

---

### 2.2 Two-State Boltzmann (TSB) Metrics

#### **Goodness of Fit: R²**

**Definition**: Coefficient of determination
```
R² = 1 - (SS_residual / SS_total)
```

| Quality Tier | R² Range | Interpretation |
|--------------|----------|----------------|
| **Excellent** ✅ | ≥ 0.95 | High confidence in Tm |
| **Good** ✅ | 0.90 - 0.95 | Acceptable fit quality |
| **Marginal** ⚠️ | 0.80 - 0.90 | Use with caution |
| **Poor** ❌ | < 0.80 | Unreliable Tm |

**What R² measures**:
- How well the TSB model explains the data
- Deviation of fitted curve from observed fluorescence
- Combined effect of noise, baseline drift, and model appropriateness

**Common causes of low R²**:
- **High noise**: SNR < 10, random fluctuations
- **Complex unfolding**: Multi-domain proteins, intermediates
- **Aggregation**: Non-sigmoidal transitions
- **Baseline issues**: Drift, photobleaching, bubbles

---

#### **Fit Convergence**

| Status | Meaning | Action |
|--------|---------|--------|
| **Converged** | Optimizer found minimum | Report Tm |
| **Failed** | Max iterations reached | Mark as ❌ |
| **Poor initial guess** | No convergence | Use multiple initial guesses |

---

### 2.3 Area Under Curve (AUC) Metrics

#### **Hill Fit R²**

AUC method fits a Hill equation to the integrated fluorescence (progress curve):
```
P(T) = Bottom + (Top - Bottom) / (1 + 10^((T₅₀ - T) × HillSlope))
```

| Quality Tier | R² Range | Interpretation |
|--------------|----------|----------------|
| **Excellent** ✅ | ≥ 0.95 | Robust Tm estimate |
| **Good** ✅ | 0.90 - 0.95 | Acceptable quality |
| **Marginal** ⚠️ | 0.80 - 0.90 | Verify visually |
| **Poor** ❌ | < 0.80 | Unreliable |

**Advantages of AUC**:
- More robust to noise than TSB
- Less sensitive to baseline model choice
- Better for screening applications

**When AUC outperforms TSB**:
- Noisy data (e.g., low protein concentration)
- Non-exponential baselines
- Partial unfolding (incomplete transitions)

---

### 2.4 First Derivative (FD) Metrics

#### **Signal-to-Noise Ratio (SNR)**

**Definition**: Peak height relative to baseline noise
```
SNR = (Peak_height - Baseline_mean) / Baseline_std
```

| Quality Tier | SNR Range | Interpretation |
|--------------|-----------|----------------|
| **Excellent** ✅ | ≥ 5.0 | Clear, sharp peak |
| **Good** ✅ | 3.0 - 5.0 | Detectable peak |
| **Marginal** ⚠️ | 2.0 - 3.0 | Weak signal |
| **Poor** ❌ | < 2.0 | Peak not reliable |

**How SNR is calculated**:
1. Compute first derivative: dF/dT using Savitzky-Golay filter
2. Identify peak: Maximum of smoothed derivative
3. Estimate baseline: Mean of derivative outside transition region
4. Calculate noise: Standard deviation of baseline
5. SNR = (Peak - Baseline) / Noise

**Factors affecting SNR**:
- **Signal strength**: Protein concentration, fluorophore content
- **Noise level**: Instrument precision, buffer conditions
- **Transition sharpness**: Cooperativity (higher = sharper peak)
- **Smoothing**: Too much blurs peak, too little amplifies noise

---

#### **Peak Width**

| Width (°C) | Interpretation | Likely Cause |
|-----------|----------------|--------------|
| 2-5°C | Normal cooperativity | Single-domain protein |
| 5-10°C | Lower cooperativity | Multi-domain or large protein |
| > 10°C | Broad transition | Aggregation, heterogeneity |
| < 2°C | Very sharp | Highly cooperative unfolding |

**Note**: Peak width is reported but not used for pass/fail criteria.

---

## Quality Assessment Criteria

### 3.1 Three-Tier System

QuantDSF uses a traffic-light system for quality assessment:

#### ✅ **PASS** (High Quality)
**Criteria**:
- TSB/AUC: R² ≥ 0.90
- FD: SNR ≥ 3.0
- Tm within reasonable range (25-100°C)
- Fit converged successfully

**Interpretation**: High confidence in reported Tm, suitable for publication and quantitative comparisons.

**Recommended use**:
- Quantitative thermal stability comparisons
- Thermodynamic analysis (Van't Hoff, ΔΔG)
- High-throughput screening hit validation

---

#### ⚠️ **WARNING** (Marginal Quality)
**Criteria**:
- TSB/AUC: 0.80 ≤ R² < 0.90
- FD: 2.0 ≤ SNR < 3.0
- Fit converged but with lower confidence
- Tm estimate less reliable

**Interpretation**: Data usable for screening but requires caution. Manual inspection recommended.

**Recommended use**:
- Initial screening (identify trends)
- Relative comparisons (same-day experiments)
- Flagged for follow-up validation

**What to check**:
- Inspect melting curve visually
- Compare with replicates
- Consider alternative analysis method
- Check experimental conditions (pH, buffer, concentration)

---

#### ❌ **FAIL** (Poor Quality)
**Criteria**:
- TSB/AUC: R² < 0.80
- FD: SNR < 2.0
- Fit failed to converge
- Tm not detected (no peak, no transition)
- Insufficient data (< 10 points)

**Interpretation**: Tm estimate unreliable or not available. Do not use for quantitative analysis.

**Common causes**:
- Poor data quality (noise, drift, artifacts)
- No melting transition in temperature range
- Sample issues (aggregation, precipitation, air bubbles)
- Inappropriate analysis method for sample type

**Recommended action**:
- Repeat experiment with optimized conditions
- Try different analysis method
- Check sample preparation
- Inspect raw data for obvious issues

---

### 3.2 Hover Tooltips

To provide transparency, QuantDSF displays detailed quality information on hover:

| Status | Tooltip Content | Example |
|--------|----------------|---------|
| ✅ | None (obvious pass) | — |
| ⚠️ | Specific issue + threshold | "Low R²: 0.856 (threshold: 0.90)" |
| ❌ | Failure reason | "Analysis failed or Tm not found" |

---

## Quality Flags and Interpretation

### 4.1 Status Indicators in Results Table

The results table displays quality status for each sample:

```
Sample         | Concentration | Tm (°C) | R²/SNR | Method | Status
---------------|---------------|---------|--------|--------|--------
BSA_Control    | —             | 65.42   | 0.997  | TSB    | ✅
Lysozyme_10uM  | 1.00e-5       | 72.18   | 0.885  | TSB    | ⚠️
ProteinX_100nM | 1.00e-7       | —       | 0.652  | TSB    | ❌
```

**Visual cues**:
- ✅ Green checkmark: High quality
- ⚠️ Yellow warning: Marginal quality (inspect visually)
- ❌ Red X: Failed analysis (do not use)

---

### 4.2 Sorting and Filtering

**Default sort order**:
1. By status (✅ → ⚠️ → ❌)
2. By concentration (low to high)
3. Alphabetically by sample name

**Recommended workflow**:
1. Review ❌ samples: Identify common failure modes
2. Inspect ⚠️ samples: Decide if acceptable for purpose
3. Analyze ✅ samples: Proceed with downstream analysis

---

## Method-Specific Quality Control

### 5.1 When to Use Each Method

| Method | Best For | Strengths | Weaknesses | QC Metric |
|--------|----------|-----------|------------|-----------|
| **TSB** | Clean data, single transitions | Thermodynamic parameters, high precision | Sensitive to noise and baselines | R² |
| **AUC** | Noisy data, screening | Robust to noise, fast | Less precise Tm | R² |
| **FD** | Quick screening, no fitting | Very fast, model-free | Sensitive to noise, no thermodynamics | SNR |

---

### 5.2 Switching Methods for Quality Improvement

**Scenario 1**: TSB gives low R² (0.85) but data looks reasonable
- **Try**: AUC method
- **Reason**: AUC is more robust to baseline model misspecification

**Scenario 2**: FD gives low SNR (2.5) but peak is visible
- **Try**: TSB or AUC
- **Reason**: Fitting methods can extract Tm from noisy data better than derivative

**Scenario 3**: All methods fail (❌)
- **Action**: Inspect raw data for experimental issues
- **Consider**: Repeat experiment, adjust conditions

---

### 5.3 TSB Advanced Settings

For difficult samples with low TSB R², users can adjust:

1. **Smoothing Level** (Savitzky-Golay filter)
   - **Low** (window=5): Preserve sharp transitions, noisier
   - **Medium** (window=9, default): Balanced
   - **High** (window=13): Smoother curves, may blur peaks

2. **Baseline Model**
   - **Exponential** (default): Standard for DSF
   - **Linear**: For short temperature ranges

**Effect on quality**:
- Increased smoothing → Higher R² but lower resolution
- Optimal balance depends on noise level

---

## Experimental Design Guidelines

### 6.1 Recommended Parameters

#### **For High-Quality Tm Determination**

| Parameter | Recommended | Minimum | Notes |
|-----------|-------------|---------|-------|
| **Temperature Range** | 20-95°C | Tm ± 15°C | Capture full transition |
| **Step Size** | 0.5-1.0°C | 1.0°C | Finer steps → better resolution |
| **Ramp Rate** | 1°C/min | 0.5°C/min | Slower → equilibrium |
| **Protein Concentration** | 0.1-1.0 mg/mL | 0.05 mg/mL | Higher → better SNR |
| **Replicates** | ≥ 3 | ≥ 2 | Assess reproducibility |
| **Channel** | 350/330 nm ratio | — | Most robust signal |

---

#### **For Thermodynamic Analysis (Van't Hoff)**

| Parameter | Recommended | Minimum | Notes |
|-----------|-------------|---------|-------|
| **Concentration Points** | 5-8 | 3 | More points → better fit |
| **Concentration Range** | 2-3 log units | 1 log unit | Cover KD ± 10× |
| **Spacing** | Logarithmic | — | Even coverage on log scale |
| **Replicates per [L]** | ≥ 2 | 1 | Assess variability |
| **Include Apo** | Yes | Yes | Establish baseline Tm |

**Example concentration series (KD ~ 1 µM)**:
```
0 µM (apo), 0.1, 0.3, 1, 3, 10, 30 µM
```

---

#### **For Dose-Response (EC₅₀ Determination)**

| Parameter | Recommended | Minimum | Notes |
|-----------|-------------|---------|-------|
| **Concentration Points** | 8-12 | 6 | Resolve Hill slope |
| **Range** | EC₅₀ ± 2 log | EC₅₀ ± 1 log | Capture full curve |
| **Spacing** | Logarithmic | — | Equal spacing on log scale |
| **Controls** | Apo + saturating | Apo | Establish bounds |

---

### 6.2 Instrument Settings

#### **Prometheus NT.Panta**
- **Excitation**: 280 nm (intrinsic Trp/Tyr)
- **Emission**: 330 nm + 350 nm
- **Capillaries**: Standard or high-sensitivity
- **Sample Volume**: 10 µL (standard)
- **Power**: 10-100% (optimize for signal)

#### **Tycho NT.6**
- **LED Power**: Auto or 50-100%
- **Sample Volume**: 10 µL
- **Capillaries**: 6 per run
- **Channels**: All three (ratio, 330, 350)

---

### 6.3 Sample Preparation

**Critical factors**:
1. **Buffer Choice**
   - pH 7-8 (physiological)
   - Low ionic strength if studying ionic interactions
   - Avoid HEPES at high pH (protonation changes with T)

2. **Sample Quality**
   - Centrifuge (10 min, 14,000×g) to remove aggregates
   - Filter if needed (0.22 µm)
   - Check A280 for accurate concentration

3. **Controls**
   - **Apo protein**: No ligand (baseline Tm)
   - **Known stabilizer**: Positive control (e.g., substrate analog)
   - **Buffer blank**: Check for artifacts

4. **Replicates**
   - Technical replicates: Same sample, multiple capillaries (assess instrument variability)
   - Biological replicates: Independent preparations (assess prep-to-prep variation)

---

## Troubleshooting Guide

### 7.1 Common Issues and Solutions

#### **Issue 1: Low R² (TSB/AUC < 0.90)**

| Possible Cause | Diagnostic | Solution |
|----------------|-----------|----------|
| **Noisy signal** | High scatter in curve | • Increase protein concentration<br>• Use AUC instead of TSB<br>• Increase smoothing |
| **Multiple transitions** | Shoulders, inflections | • Protein may have multiple domains<br>• Try FD to identify peaks<br>• Fit individual domains separately |
| **Baseline drift** | Non-flat pre/post transition | • Check for bubbles, precipitation<br>• Adjust baseline model<br>• Re-run with fresh sample |
| **Incomplete unfolding** | No upper plateau | • Extend temperature range<br>• Increase to 95°C or higher<br>• May be irreversible aggregation |

---

#### **Issue 2: Low SNR (FD < 3.0)**

| Possible Cause | Diagnostic | Solution |
|----------------|-----------|----------|
| **Weak signal** | Low amplitude | • Increase protein concentration<br>• Check Trp/Tyr content<br>• Use TSB/AUC instead |
| **Broad transition** | Wide peak (> 10°C) | • Expected for multi-domain proteins<br>• Lower SNR is normal<br>• Use TSB for quantification |
| **High noise** | Spiky derivative | • Increase smoothing<br>• Check for bubbles/debris<br>• Centrifuge sample |
| **No transition** | Flat derivative | • Extend temperature range<br>• Check protein is folded<br>• Verify sample identity |

---

#### **Issue 3: Tm Not Detected (❌)**

| Possible Cause | Diagnostic | Solution |
|----------------|-----------|----------|
| **Tm outside range** | No transition visible | • Extend temperature range<br>• Check expected Tm for protein |
| **Protein already denatured** | Flat signal | • Check sample storage<br>• Prepare fresh sample<br>• Verify folding (CD, activity) |
| **Aggregation** | Turbidity, scatter | • Centrifuge before loading<br>• Lower concentration<br>• Add detergent/stabilizer |
| **Reversible oligomerization** | Concentration-dependent | • Run dilution series<br>• Check monomer fraction (SEC) |

---

#### **Issue 4: Poor Reproducibility (High CV)**

| Possible Cause | Diagnostic | Solution |
|----------------|-----------|----------|
| **Sample heterogeneity** | CV > 5% | • Filter/centrifuge<br>• Check for aggregation (DLS)<br>• Prepare fresh sample |
| **Instrument variability** | CV 2-5% | • Normal for nanoDSF<br>• Use more replicates<br>• Calibrate instrument |
| **Buffer mismatch** | Systematic shift | • Ensure all samples in same buffer<br>• Dialyze if needed |
| **Temperature calibration** | Consistent offset | • Run Tm standard (lysozyme, BSA)<br>• Calibrate instrument |

---

#### **Issue 5: Concentration Not Detected**

| Problem | Example | Solution |
|---------|---------|----------|
| **Non-standard format** | `10microM` | Use `10uM`, `10µM`, or `10 uM` |
| **Missing unit** | `Sample_10` | Add unit: `Sample_10uM` |
| **Unit in wrong place** | `uM10_Sample` | Move to end: `Sample_10uM` |
| **Ambiguous** | `0.1` | Specify unit: `0.1uM` or `100nM` |

---

### 7.2 Systematic Quality Issues

#### **All samples have low quality**

**Likely causes**:
1. Instrument issue (LED power, detector)
2. Buffer incompatibility (pH, ionic strength)
3. Universal sample issue (old stock, wrong buffer)
4. Wrong analysis method for sample type

**Recommended action**:
1. Run positive control (lysozyme, BSA)
2. Check instrument calibration
3. Verify buffer composition
4. Re-prepare samples from fresh stock

---

#### **Specific condition always fails**

**Example**: All samples with ligand X show ❌

**Possible causes**:
1. Ligand causes aggregation
2. Ligand absorbs/fluoresces at detection wavelength
3. Ligand destabilizes beyond temperature range
4. Solubility issue (precipitation)

**Recommended action**:
1. Check ligand spectrum (UV-Vis)
2. Run ligand-only control (no protein)
3. Examine samples post-run (clarity)
4. Try different ligand concentration range

---

## Best Practices

### 8.1 Quality Control Checklist

**Before experiment**:
- [ ] Protein concentration verified (A280)
- [ ] Sample centrifuged/filtered
- [ ] Buffer composition documented
- [ ] Positive control included
- [ ] Temperature range covers expected Tm ± 15°C

**During experiment**:
- [ ] Capillaries loaded without bubbles
- [ ] Signal amplitude reasonable (not saturated)
- [ ] No obvious aggregation/precipitation

**After experiment**:
- [ ] Check % of samples with ✅ status (target: > 80%)
- [ ] Inspect ⚠️ samples visually
- [ ] Investigate systematic failures (all ❌ for one condition)
- [ ] Compare replicates (CV < 5%)

---

### 8.2 Reporting Quality Metrics

When publishing or sharing results:

**Required information**:
1. Analysis method used (TSB, AUC, FD)
2. Quality metric threshold (e.g., R² ≥ 0.90)
3. Number of replicates
4. % of samples passing QC
5. How failed samples were handled

**Example statement**:
> "Tm values were determined using the Two-State Boltzmann method in QuantDSF v2.0. Only samples with R² ≥ 0.90 were included in downstream analysis (95% pass rate, n=3 replicates per condition, CV < 3%)."

---

### 8.3 Data Archiving

**Recommended to save**:
1. Raw instrument files (.zip from Prometheus/Tycho)
2. QuantDSF results (.xlsx export)
3. Quality control summary (% pass/warn/fail)
4. Plots (melting curves, distributions)
5. Analysis settings (method, parameters)

**For reproducibility**:
- Document QuantDSF version
- Note any advanced settings used (smoothing, baseline model)
- Include experimental metadata (date, operator, instrument)

---

## Summary

QuantDSF's quality control system ensures:

✅ **Transparency**: All metrics clearly reported
✅ **Automation**: No manual scoring required
✅ **Flexibility**: Multiple methods for different data types
✅ **Clarity**: Visual indicators for immediate interpretation

**Key takeaways**:
1. Always check quality status (✅ ⚠️ ❌) before interpreting Tm
2. Use method-specific metrics (R² for TSB/AUC, SNR for FD)
3. Inspect ⚠️ samples manually before including in analysis
4. Exclude ❌ samples from quantitative comparisons
5. Optimize experimental design for high-quality data

---

## Related Documentation

- **[IO_SPECIFICATION.md](IO_SPECIFICATION.md)** - Input/output formats and error messages
- **[SMOOTHING_METHODOLOGY.md](SMOOTHING_METHODOLOGY.md)** - Signal processing details
- **[ADVANCED_SETTINGS_TSB_SMOOTHING.md](ADVANCED_SETTINGS_TSB_SMOOTHING.md)** - TSB parameter tuning

---

## Contact

For questions about quality control:
- **GitHub Issues**: [https://github.com/shuozhou87/QuantDSF/issues](https://github.com/shuozhou87/QuantDSF/issues)
- **Production Server**: http://g1200163267.win.uthscsa.edu:9051/

---

**Document End**
