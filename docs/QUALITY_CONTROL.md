# QuantDSF Quality Control Specification

**Version**: 2.1
**Last Updated**: 2026-01-09
**Status**: Production - Implementation Required

---

## Table of Contents

1. [Overview](#overview)
2. [QC Module Architecture](#qc-module-architecture)
3. [Tab 1: Basic Analysis QC](#tab-1-basic-analysis-qc)
4. [Tab 2: Thermodynamic Analysis QC](#tab-2-thermodynamic-analysis-qc)
5. [Tab 3: Dose-Response QC](#tab-3-dose-response-qc)
6. [Quality Flags System](#quality-flags-system)
7. [Implementation Guidelines](#implementation-guidelines)
8. [Experimental Design Guidelines](#experimental-design-guidelines)
9. [Troubleshooting Guide](#troubleshooting-guide)

---

## Overview

QuantDSF implements tab-specific quality control systems to ensure reliable analysis at each stage:

- **Tab 1 (Basic Analysis)**: Per-capillary Tm determination quality
- **Tab 2 (Thermodynamics)**: Van't Hoff regression and thermodynamic parameter reliability
- **Tab 3 (Dose-Response)**: 4PL fitting quality for EC₅₀ determination

### Design Philosophy

1. **Modular Architecture**: QC logic separated from analysis code
2. **Tab-Specific Metrics**: Each tab has appropriate QC criteria
3. **Automated Assessment**: All metrics calculated automatically
4. **Transparent Reporting**: Users see all quality parameters
5. **Three-Tier System**: ✅ Pass, ⚠️ Warning, ❌ Fail

---

## QC Module Architecture

### 2.1 Module Structure

```
core/
└── qc/
    ├── __init__.py
    ├── base.py              # Base QC classes
    ├── tm_qc.py             # Tab 1: Tm quality control
    ├── thermo_qc.py         # Tab 2: Thermodynamic QC
    ├── dose_response_qc.py  # Tab 3: Dose-response QC
    └── metrics.py           # Common QC metrics
```

### 2.2 Base QC Interface

```python
class QualityCheck(BaseModel):
    """Base quality check result"""
    passed: bool
    flag: Literal['✅', '⚠️', '❌']
    score: float  # 0-100
    message: str
    details: Dict[str, Any]

class QualityController(ABC):
    """Abstract base for QC modules"""

    @abstractmethod
    def evaluate(self, data: Any) -> QualityCheck:
        """Evaluate quality and return result"""
        pass

    @abstractmethod
    def get_metrics(self, data: Any) -> Dict[str, float]:
        """Calculate all QC metrics"""
        pass
```

### 2.3 Design Principles

**Separation of Concerns**:
- Analysis code: Focused on calculation (Tm, thermodynamics, fitting)
- QC code: Focused on quality assessment
- UI code: Displays QC results

**Centralized Logic**:
- All QC thresholds defined in one place
- Consistent flag assignment across tabs
- Easy to update criteria globally

**Extensibility**:
- New QC metrics can be added without modifying analysis code
- Tab-specific QC inherits from base class
- Configurable thresholds via settings

---

## Tab 1: Basic Analysis QC

### 3.1 Overview

Tab 1 QC evaluates the quality of individual Tm measurements for each capillary, regardless of analysis method (TSB, AUC, FD).

### 3.2 Quality Metrics

#### **A. Universal Metrics (All Methods)**

##### **Data Completeness**

| Metric | Threshold | Flag if Failed |
|--------|-----------|----------------|
| Valid Data Points | ≥ 10 | ❌ |
| Temperature Range | ≥ 20°C | ⚠️ |
| Non-NaN Ratio | ≥ 95% | ⚠️ |

**Implementation**:
```python
def check_data_completeness(T, F):
    n_valid = np.sum(~np.isnan(T) & ~np.isnan(F))
    t_range = np.ptp(T)
    nan_ratio = np.sum(np.isnan(F)) / len(F)

    return {
        'n_valid': n_valid,
        't_range': t_range,
        'nan_ratio': nan_ratio,
        'passed': n_valid >= 10 and t_range >= 20 and nan_ratio < 0.05
    }
```

---

##### **Signal Quality**

| Metric | Threshold | Flag if Failed |
|--------|-----------|----------------|
| Dynamic Range | > 5% of max(F) | ⚠️ |
| Baseline SNR | ≥ 5.0 | ⚠️ |

**Dynamic Range**: `ΔF = max(F) - min(F)`

**Baseline SNR**: Ratio of signal to baseline noise
```
SNR_baseline = (max(F) - min(F)) / std(F[:baseline_region])
```

---

#### **B. TSB-Specific Metrics**

##### **B1. Goodness of Fit: R²**

| Quality Tier | R² Range | Flag |
|--------------|----------|------|
| Excellent | ≥ 0.95 | ✅ |
| Good | 0.90 - 0.95 | ✅ |
| Marginal | 0.80 - 0.90 | ⚠️ |
| Poor | < 0.80 | ❌ |

**Calculation**:
```
SS_res = Σ(F_obs - F_fit)²
SS_tot = Σ(F_obs - F_mean)²
R² = 1 - (SS_res / SS_tot)
```

---

##### **B2. State SNR** ⭐ **[FROM V1 - NEEDS IMPLEMENTATION]**

**Definition**: Signal-to-noise ratio of the two-state transition

```
State SNR = |F_D(Tm) - F_N(Tm)| / σ_residual
```

Where:
- `F_N(Tm) = A_N·exp(α·Tm) + D_N` (native state fluorescence at Tm)
- `F_D(Tm) = A_D·exp(β·Tm) + D_D` (denatured state fluorescence at Tm)
- `σ_residual = sqrt(RSS / df)` (residual standard error)

| Quality Tier | State SNR | Interpretation |
|--------------|-----------|----------------|
| **Excellent** ✅ | ≥ 10.0 | Well-defined transition |
| **Good** ✅ | 5.0 - 10.0 | Clear transition |
| **Marginal** ⚠️ | 3.0 - 5.0 | Weak but detectable |
| **Poor** ❌ | < 3.0 | Poorly defined states |

**Why State SNR matters**:
- R² only measures overall fit quality
- State SNR measures how well the two states (N and D) are separated
- High R² with low State SNR → Good fit but unclear transition
- Critical for multi-domain proteins

**Example**:
```python
def calculate_state_snr(T, F, popt, F_fit):
    """
    Calculate state SNR for TSB fit

    Args:
        T: Temperature array
        F: Observed fluorescence
        popt: Fitted parameters [A_N, α, D_N, A_D, β, D_D, Tm, k]
        F_fit: Fitted fluorescence

    Returns:
        state_snr: float
    """
    A_N, alpha, D_N, A_D, beta, D_D, Tm, k = popt

    # Calculate fluorescence of N and D states at Tm
    F_N = A_N * np.exp(alpha * Tm) + D_N
    F_D = A_D * np.exp(beta * Tm) + D_D

    # Calculate residual standard error
    residuals = F - F_fit
    rss = np.sum(residuals**2)
    df = len(F) - len(popt)
    sigma_residual = np.sqrt(rss / df)

    # State SNR
    state_snr = abs(F_D - F_N) / sigma_residual

    return state_snr
```

---

##### **B3. Model Selection: ΔAIC** ⭐ **[FROM V1 - NEEDS IMPLEMENTATION]**

**Definition**: Akaike Information Criterion difference between linear and TSB models

```
AIC = n·ln(RSS/n) + 2·k

AIC_linear = n·ln(RSS_linear/n) + 2·3   # 3 parameters: slope, intercept, Tm
AIC_TSB = n·ln(RSS_TSB/n) + 2·8         # 8 parameters

ΔAIC = AIC_linear - AIC_TSB
log₁₀(ΔAIC) = preferred metric for interpretation
```

| log₁₀(ΔAIC) | Interpretation | Flag |
|-------------|----------------|------|
| ≥ 2.0 | TSB strongly preferred | ✅ |
| 1.0 - 2.0 | TSB preferred | ✅ |
| 0.5 - 1.0 | TSB marginally better | ⚠️ |
| < 0.5 | Linear model sufficient | ⚠️ |

**Why ΔAIC matters**:
- Balances fit quality with model complexity
- Detects overfitting (TSB may fit noise)
- Low ΔAIC → Transition too simple for TSB, use AUC/FD instead

**Implementation**:
```python
def calculate_delta_aic(T, F, Tm_linear, popt_tsb, F_fit_tsb):
    """
    Calculate ΔAIC between linear and TSB models

    Args:
        T: Temperature array
        F: Observed fluorescence
        Tm_linear: Tm from linear interpolation
        popt_tsb: TSB fitted parameters
        F_fit_tsb: TSB fitted fluorescence

    Returns:
        delta_aic: float
        log_delta_aic: float (preferred for reporting)
    """
    n = len(F)

    # Linear model: 3-parameter (pre-slope, post-slope, Tm)
    # Fit linear baselines and compute RSS
    idx_pre = T < Tm_linear - 5
    idx_post = T > Tm_linear + 5

    if np.sum(idx_pre) > 2 and np.sum(idx_post) > 2:
        # Fit pre-transition baseline
        p_pre = np.polyfit(T[idx_pre], F[idx_pre], 1)
        F_pre = np.polyval(p_pre, T)

        # Fit post-transition baseline
        p_post = np.polyfit(T[idx_post], F[idx_post], 1)
        F_post = np.polyval(p_post, T)

        # Linear model: average of two baselines in transition
        F_linear = np.where(T < Tm_linear, F_pre, F_post)
        RSS_linear = np.sum((F - F_linear)**2)
    else:
        # Fallback: simple linear fit
        p = np.polyfit(T, F, 1)
        F_linear = np.polyval(p, T)
        RSS_linear = np.sum((F - F_linear)**2)

    # TSB model RSS
    RSS_tsb = np.sum((F - F_fit_tsb)**2)

    # Calculate AIC
    AIC_linear = n * np.log(RSS_linear / n) + 2 * 3
    AIC_tsb = n * np.log(RSS_tsb / n) + 2 * 8

    delta_aic = AIC_linear - AIC_tsb
    log_delta_aic = np.log10(delta_aic) if delta_aic > 0 else 0.0

    return delta_aic, log_delta_aic
```

---

##### **B4. Tm Uncertainty**

| Tm Error (°C) | Quality | Flag |
|---------------|---------|------|
| < 0.5 | Excellent | ✅ |
| 0.5 - 1.0 | Good | ✅ |
| 1.0 - 2.0 | Marginal | ⚠️ |
| > 2.0 | Poor | ❌ |

**Calculation**: Standard error from covariance matrix
```
Tm_error = sqrt(pcov[6,6])  # Tm is parameter index 6
```

---

#### **C. AUC-Specific Metrics**

##### **C1. Hill Fit R²**

Same thresholds as TSB:

| Quality Tier | R² Range | Flag |
|--------------|----------|------|
| ≥ 0.95 | Excellent | ✅ |
| 0.90 - 0.95 | Good | ✅ |
| 0.80 - 0.90 | Marginal | ⚠️ |
| < 0.80 | Poor | ❌ |

##### **C2. Dynamic Range**

| Dynamic Range | Quality | Flag |
|---------------|---------|------|
| > 80% | Excellent | ✅ |
| 60-80% | Good | ✅ |
| 40-60% | Marginal | ⚠️ |
| < 40% | Poor | ❌ |

**Calculation**:
```
Progress curve: P(T) from integration of F(T)
Dynamic Range = (P_max - P_min) / P_max × 100%
```

---

#### **D. First Derivative (FD) Specific Metrics**

##### **D1. Peak SNR**

| Peak SNR | Quality | Flag |
|----------|---------|------|
| ≥ 5.0 | Excellent | ✅ |
| 3.0 - 5.0 | Good | ✅ |
| 2.0 - 3.0 | Marginal | ⚠️ |
| < 2.0 | Poor | ❌ |

**Calculation**:
```
dF/dT = first derivative (Savitzky-Golay smoothed)
Peak_height = max(dF/dT)
Baseline_mean = mean(dF/dT[baseline_region])
Baseline_std = std(dF/dT[baseline_region])

Peak SNR = (Peak_height - Baseline_mean) / Baseline_std
```

##### **D2. Peak Width**

| Width (°C) | Interpretation | Flag |
|-----------|----------------|------|
| 2-5 | Normal cooperativity | ✅ |
| 5-10 | Lower cooperativity | ✅ |
| > 10 | Broad transition | ⚠️ |
| < 2 | Very sharp (may be artifact) | ⚠️ |

**Calculation**: Full width at half maximum (FWHM)

---

### 3.3 Overall Quality Flag (Tab 1)

**Flag Assignment Logic**:

```python
def assign_tab1_quality_flag(metrics, method):
    """
    Assign overall quality flag for Tab 1

    Args:
        metrics: Dict of all QC metrics
        method: 'boltzmann', 'auc', or 'derivative'

    Returns:
        flag: '✅', '⚠️', or '❌'
    """
    # Check critical failures
    if metrics['n_valid'] < 10:
        return '❌'

    if np.isnan(metrics['tm']):
        return '❌'

    # Method-specific checks
    if method == 'boltzmann':
        if metrics['r_squared'] < 0.80:
            return '❌'
        elif metrics['r_squared'] < 0.90:
            return '⚠️'
        elif metrics.get('state_snr', float('inf')) < 3.0:
            return '⚠️'
        else:
            return '✅'

    elif method == 'auc':
        if metrics['r_squared'] < 0.80:
            return '❌'
        elif metrics['r_squared'] < 0.90:
            return '⚠️'
        else:
            return '✅'

    elif method == 'derivative':
        if metrics['peak_snr'] < 2.0:
            return '❌'
        elif metrics['peak_snr'] < 3.0:
            return '⚠️'
        else:
            return '✅'

    return '⚠️'  # Default
```

---

## Tab 2: Thermodynamic Analysis QC

### 4.1 Overview

Tab 2 QC evaluates the reliability of thermodynamic parameters (ΔH, ΔS, KD) derived from Van't Hoff analysis.

### 4.2 Quality Metrics

#### **A. Van't Hoff Regression Quality**

##### **A1. Regression R²**

| R² Range | Quality | Reliability |
|----------|---------|-------------|
| ≥ 0.95 | Excellent | HIGH |
| 0.90 - 0.95 | Good | MEDIUM |
| 0.85 - 0.90 | Marginal | LOW |
| < 0.85 | Poor | VERY LOW |

**Calculation**:
```
Van't Hoff plot: ln(KD) vs 1/T

R² = 1 - (SS_residual / SS_total)
```

---

##### **A2. Number of Data Points**

| n_points | Quality | Flag |
|----------|---------|------|
| ≥ 5 | Excellent | ✅ |
| 3-4 | Acceptable | ⚠️ |
| < 3 | Insufficient | ❌ |

**Why it matters**:
- n < 3: Cannot perform regression
- n = 3-4: Regression possible but low confidence
- n ≥ 5: Recommended for reliable ΔH, ΔS

---

##### **A3. Temperature Range**

| ΔT (K) | Quality | Flag |
|--------|---------|------|
| ≥ 15 | Good | ✅ |
| 10-15 | Marginal | ⚠️ |
| < 10 | Poor | ❌ |

**Why it matters**:
- Narrow ΔT → High extrapolation error
- Wide ΔT → Reliable KD prediction at target temperatures

---

#### **B. Parameter Uncertainty**

##### **B1. ΔH Relative Error**

| Relative Error | Quality | Flag |
|----------------|---------|------|
| < 10% | Excellent | ✅ |
| 10-20% | Good | ✅ |
| 20-30% | Marginal | ⚠️ |
| > 30% | Poor | ❌ |

**Calculation**:
```
ΔH_error = sqrt(cov[0,0])  # From regression covariance
Relative_error = ΔH_error / |ΔH| × 100%
```

---

##### **B2. ΔS Relative Error**

Same thresholds as ΔH.

---

##### **B3. KD Prediction Reliability**

**Extrapolation Factor**: Distance from measured temperature range

```
T_target = 298K or 310K
T_measured_range = [T_min, T_max]

Extrapolation_factor = min(|T_target - T_min|, |T_target - T_max|) / (T_max - T_min)
```

| Extrapolation Factor | Reliability | Flag |
|---------------------|-------------|------|
| < 0.5 | HIGH (interpolation) | ✅ |
| 0.5 - 1.0 | MEDIUM (mild extrapolation) | ⚠️ |
| 1.0 - 2.0 | LOW (significant extrapolation) | ⚠️ |
| > 2.0 | VERY LOW (extreme extrapolation) | ❌ |

---

#### **C. Physical Plausibility**

##### **C1. ΔH Range Check**

| ΔH (kJ/mol) | Interpretation | Flag |
|-------------|----------------|------|
| -800 to -50 | Typical for protein unfolding | ✅ |
| -1200 to -800 or -50 to 0 | Unusual but possible | ⚠️ |
| < -1200 or > 0 | Unphysical | ❌ |

---

##### **C2. ΔS Range Check**

| ΔS (J/mol/K) | Interpretation | Flag |
|--------------|----------------|------|
| -3000 to -200 | Typical | ✅ |
| -4000 to -3000 or -200 to 0 | Unusual | ⚠️ |
| < -4000 or > 0 | Unphysical | ❌ |

**Note**: For ligand binding (not protein unfolding), typical ranges differ

---

### 4.3 Overall Thermodynamic Quality Assessment

**Combined Reliability Level**:

```python
def assess_thermodynamic_quality(vh_result):
    """
    Assess overall thermodynamic analysis quality

    Returns:
        reliability: 'HIGH', 'MEDIUM', 'LOW', 'VERY LOW'
        flag: '✅', '⚠️', '❌'
    """
    r2 = vh_result.r_squared
    n = vh_result.n_points
    delta_T = vh_result.t_range

    # Critical failures
    if n < 3 or r2 < 0.85:
        return 'VERY LOW', '❌'

    # Score-based assessment
    score = 0

    # Regression quality (40 points)
    if r2 >= 0.95:
        score += 40
    elif r2 >= 0.90:
        score += 30
    else:
        score += 20

    # Data sufficiency (30 points)
    if n >= 5:
        score += 30
    elif n >= 3:
        score += 15

    # Temperature range (20 points)
    if delta_T >= 15:
        score += 20
    elif delta_T >= 10:
        score += 10

    # Physical plausibility (10 points)
    if -800 < vh_result.delta_h < -50:
        score += 10
    elif -1200 < vh_result.delta_h < 0:
        score += 5

    # Assign reliability
    if score >= 80:
        return 'HIGH', '✅'
    elif score >= 60:
        return 'MEDIUM', '⚠️'
    elif score >= 40:
        return 'LOW', '⚠️'
    else:
        return 'VERY LOW', '❌'
```

---

## Tab 3: Dose-Response QC

### 5.1 Overview

Tab 3 QC evaluates the quality of 4-parameter logistic (4PL) fits for EC₅₀ determination from isothermal dose-response curves.

### 5.2 Quality Metrics

#### **A. 4PL Fit Quality**

##### **A1. Regression R²**

| R² Range | Quality | Flag |
|----------|---------|------|
| ≥ 0.95 | Excellent | ✅ |
| 0.90 - 0.95 | Good | ✅ |
| 0.85 - 0.90 | Marginal | ⚠️ |
| < 0.85 | Poor | ❌ |

---

##### **A2. Dynamic Range**

```
Dynamic Range = (Top - Bottom) / Top × 100%
```

| Dynamic Range | Quality | Flag |
|---------------|---------|------|
| > 60% | Excellent | ✅ |
| 40-60% | Good | ✅ |
| 20-40% | Marginal | ⚠️ |
| < 20% | Poor | ❌ |

**Why it matters**:
- Low dynamic range → EC₅₀ poorly defined
- Weak ligand response → Consider higher concentrations

---

##### **A3. Hill Slope**

| Hill Slope | Interpretation | Flag |
|-----------|----------------|------|
| 0.8 - 2.0 | Normal cooperativity | ✅ |
| 0.5 - 0.8 or 2.0 - 3.0 | Unusual cooperativity | ⚠️ |
| < 0.5 or > 3.0 | Questionable | ❌ |

**Why it matters**:
- Hill slope ≈ 1: Non-cooperative binding
- Hill slope > 1: Positive cooperativity
- Hill slope < 0.5 or > 3: May indicate fitting artifact

---

#### **B. Data Coverage**

##### **B1. Number of Concentrations**

| n_concentrations | Quality | Flag |
|------------------|---------|------|
| ≥ 8 | Excellent | ✅ |
| 6-7 | Good | ✅ |
| 4-5 | Marginal | ⚠️ |
| < 4 | Insufficient | ❌ |

---

##### **B2. Concentration Range**

**Coverage of EC₅₀**:

```
Coverage = log₁₀(C_max / C_min)
```

| Coverage (log units) | Quality | Flag |
|---------------------|---------|------|
| ≥ 3 | Excellent | ✅ |
| 2-3 | Good | ✅ |
| 1-2 | Marginal | ⚠️ |
| < 1 | Narrow | ❌ |

**Bracket Check**: Does concentration range include EC₅₀?

| Status | Flag |
|--------|------|
| C_min < EC₅₀ < C_max | ✅ |
| EC₅₀ near edge (within 0.5 log) | ⚠️ |
| EC₅₀ outside range | ❌ |

---

#### **C. Baseline Quality**

##### **C1. Bottom Plateau**

Check if low concentrations reach stable baseline:

```
CV_bottom = std(Response[C < EC₅₀/10]) / mean(Response[C < EC₅₀/10])
```

| CV_bottom | Quality | Flag |
|-----------|---------|------|
| < 5% | Stable | ✅ |
| 5-10% | Moderate noise | ⚠️ |
| > 10% | Noisy | ❌ |

---

##### **C2. Top Plateau**

Check if high concentrations reach saturation:

```
CV_top = std(Response[C > EC₅₀×10]) / mean(Response[C > EC₅₀×10])
```

Same thresholds as Bottom Plateau.

---

### 5.3 Overall Dose-Response Quality

```python
def assess_dose_response_quality(dr_result):
    """
    Assess dose-response fitting quality

    Returns:
        flag: '✅', '⚠️', '❌'
        message: str
    """
    r2 = dr_result.r_squared
    n = dr_result.n_points
    dynamic_range = dr_result.dynamic_range
    hill_slope = dr_result.hill_slope

    # Critical failures
    if n < 4 or r2 < 0.85:
        return '❌', 'Insufficient data or poor fit'

    if dynamic_range < 20:
        return '❌', 'Dynamic range too low'

    # Warning conditions
    warnings = []

    if r2 < 0.90:
        warnings.append(f'Low R²: {r2:.3f}')

    if n < 6:
        warnings.append(f'Few concentrations: {n}')

    if dynamic_range < 40:
        warnings.append(f'Low dynamic range: {dynamic_range:.1f}%')

    if hill_slope < 0.5 or hill_slope > 3.0:
        warnings.append(f'Unusual Hill slope: {hill_slope:.2f}')

    if warnings:
        return '⚠️', '; '.join(warnings)
    else:
        return '✅', 'High quality fit'
```

---

## Quality Flags System

### 6.1 Three-Tier System

| Flag | Meaning | Criteria | User Action |
|------|---------|----------|-------------|
| ✅ | **PASS** | Meets all quality criteria | Use for quantitative analysis |
| ⚠️ | **WARNING** | Marginal quality, use with caution | Inspect visually, consider repeating |
| ❌ | **FAIL** | Poor quality or failed | Exclude from analysis, troubleshoot |

### 6.2 Hover Tooltips

To provide transparency, display detailed quality information on hover:

| Flag | Tooltip Content | Example |
|------|----------------|---------|
| ✅ | Brief summary or none | "R²=0.997, State SNR=12.5" |
| ⚠️ | Specific issue + threshold | "Low R²: 0.856 (threshold: 0.90); State SNR: 4.2 (threshold: 5.0)" |
| ❌ | Failure reason | "Fit failed to converge" or "Tm not found" |

---

## Implementation Guidelines

### 7.1 Code Structure

**Module: `core/qc/`**

```python
# core/qc/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Dict, Any, Literal

class QualityMetrics(BaseModel):
    """Base QC metrics"""
    passed: bool
    flag: Literal['✅', '⚠️', '❌']
    score: float  # 0-100
    message: str
    details: Dict[str, Any]

class QualityController(ABC):
    """Abstract QC controller"""

    @abstractmethod
    def evaluate(self, data: Any) -> QualityMetrics:
        pass

    @abstractmethod
    def get_metrics(self, data: Any) -> Dict[str, float]:
        pass

# core/qc/tm_qc.py
class TmQualityController(QualityController):
    """Tab 1: Tm quality control"""

    def evaluate(self, tm_result: TmResult) -> QualityMetrics:
        """Evaluate Tm result quality"""
        metrics = self.get_metrics(tm_result)
        flag = self._assign_flag(metrics, tm_result.method)
        score = self._calculate_score(metrics)
        message = self._generate_message(metrics, flag)

        return QualityMetrics(
            passed=(flag == '✅'),
            flag=flag,
            score=score,
            message=message,
            details=metrics
        )

    def get_metrics(self, tm_result: TmResult) -> Dict[str, float]:
        """Calculate all QC metrics for Tm"""
        if tm_result.method == 'boltzmann':
            return {
                'r_squared': tm_result.r_squared,
                'state_snr': self._calculate_state_snr(tm_result),
                'delta_aic': self._calculate_delta_aic(tm_result),
                'tm_error': tm_result.tm_error or 0.0,
                'n_points': len(tm_result.raw_data.T),
                't_range': tm_result.raw_data.T.ptp()
            }
        # ... similar for auc, derivative

# core/qc/thermo_qc.py
class ThermodynamicQualityController(QualityController):
    """Tab 2: Thermodynamic analysis QC"""
    # Similar structure

# core/qc/dose_response_qc.py
class DoseResponseQualityController(QualityController):
    """Tab 3: Dose-response QC"""
    # Similar structure
```

### 7.2 Integration with Analysis Code

**Before** (V2 current):
```python
# In tm/boltzmann.py
def analyze_tm_boltzmann(data):
    # ... fitting code ...
    tm_result = TmResult(
        tm=tm,
        r_squared=r2,
        # ... other fields ...
        quality_flag='⚠️' if r2 < 0.90 else '✅'  # INLINE QC - BAD
    )
    return tm_result
```

**After** (V2 with QC module):
```python
# In tm/boltzmann.py
def analyze_tm_boltzmann(data):
    # ... fitting code ...
    tm_result = TmResult(
        tm=tm,
        r_squared=r2,
        # ... other fields ...
        # NO quality_flag here - will be added by QC module
    )
    return tm_result

# In analysis pipeline (callbacks or orchestrator)
from core.qc import TmQualityController

qc = TmQualityController()
tm_result = analyze_tm_boltzmann(data)
qc_metrics = qc.evaluate(tm_result)

# Add QC info to result
tm_result.quality_flag = qc_metrics.flag
tm_result.qc_score = qc_metrics.score
tm_result.qc_details = qc_metrics.details
```

### 7.3 Configuration

Allow users to adjust QC thresholds via settings:

```python
# core/qc/config.py
class QCSettings(BaseModel):
    """QC threshold configuration"""

    # Tab 1: Tm QC
    tm_r2_excellent: float = 0.95
    tm_r2_good: float = 0.90
    tm_r2_marginal: float = 0.80

    tm_state_snr_excellent: float = 10.0
    tm_state_snr_good: float = 5.0
    tm_state_snr_marginal: float = 3.0

    tm_delta_aic_strong: float = 2.0
    tm_delta_aic_preferred: float = 1.0

    # Tab 2: Thermodynamic QC
    thermo_r2_excellent: float = 0.95
    thermo_r2_good: float = 0.90
    thermo_min_points: int = 3

    # Tab 3: Dose-response QC
    dr_r2_excellent: float = 0.95
    dr_r2_good: float = 0.90
    dr_min_dynamic_range: float = 40.0

# Load from config file or use defaults
qc_settings = QCSettings.load_from_config()
```

---

## Experimental Design Guidelines

### 8.1 For High-Quality Tm Determination (Tab 1)

| Parameter | Recommended | Minimum |
|-----------|-------------|---------|
| Temperature Range | 20-95°C | Tm ± 15°C |
| Step Size | 0.5-1.0°C | 1.0°C |
| Protein Concentration | 0.1-1.0 mg/mL | 0.05 mg/mL |
| Replicates | ≥ 3 | ≥ 2 |
| Channel | 350/330 nm ratio | — |

### 8.2 For Thermodynamic Analysis (Tab 2)

| Parameter | Recommended | Minimum |
|-----------|-------------|---------|
| Concentration Points | 5-8 | 3 |
| Concentration Range | 2-3 log units | 1 log unit |
| Temperature Range (of Tms) | ≥ 15°C | ≥ 10°C |
| Replicates per [L] | ≥ 2 | 1 |

### 8.3 For Dose-Response (Tab 3)

| Parameter | Recommended | Minimum |
|-----------|-------------|---------|
| Concentration Points | 8-12 | 6 |
| Concentration Range | EC₅₀ ± 2 log | EC₅₀ ± 1 log |
| Include Apo | Yes | Yes |
| Include Saturation | Yes | Yes |

---

## Troubleshooting Guide

### 9.1 Tab 1: Tm Quality Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Low R² (TSB) | Noisy data, complex unfolding | Try AUC method; increase smoothing |
| Low State SNR | Weak transition, multi-domain | Check protein stability; increase concentration |
| Low ΔAIC | Transition too simple | Use AUC/FD instead of TSB |
| Low Peak SNR (FD) | Weak signal, high noise | Use TSB/AUC; increase concentration |

### 9.2 Tab 2: Thermodynamic Quality Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Low regression R² | Scattered Tms, non-linearity | Check Tab 1 quality; exclude outliers |
| High ΔH error | Too few points, narrow ΔT | Add more concentrations; wider temperature range |
| Unphysical ΔH | Poor fits, wrong baseline | Check individual Tm fits; verify buffer conditions |
| HIGH extrapolation | Target T outside measured range | Measure Tms closer to target temperature |

### 9.3 Tab 3: Dose-Response Quality Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Low R² | Noisy data, wrong model | Check replicates; try different temperature |
| Low dynamic range | Weak ligand, poor protein quality | Increase ligand concentration; check protein activity |
| EC₅₀ not bracketed | Wrong concentration range | Expand concentration series around EC₅₀ |
| Unusual Hill slope | Cooperativity, artifacts | Check protein oligomerization; repeat experiment |

---

## Summary

QuantDSF v2.1 implements comprehensive, modular quality control across all three analysis tabs:

✅ **Tab 1 (Basic Analysis)**: Per-capillary Tm quality
- R², State SNR, ΔAIC (TSB)
- R², Dynamic Range (AUC)
- Peak SNR, Peak Width (FD)

✅ **Tab 2 (Thermodynamics)**: Van't Hoff regression reliability
- Regression R², n_points, ΔT
- Parameter uncertainty, extrapolation factor
- Physical plausibility checks

✅ **Tab 3 (Dose-Response)**: 4PL fitting quality
- R², dynamic range, Hill slope
- Concentration coverage, bracketing
- Baseline stability

**Key improvements from V1**:
- ⭐ State SNR added back to TSB QC
- ⭐ ΔAIC model selection added back
- 🔧 QC logic separated into dedicated module
- 📊 Consistent three-tier flagging across all tabs
- 🎯 Tab-specific QC criteria clearly defined

---

## Related Documentation

- **[IO_SPECIFICATION.md](IO_SPECIFICATION.md)** - Input/output formats
- **[SMOOTHING_METHODOLOGY.md](SMOOTHING_METHODOLOGY.md)** - Signal processing
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Implementation details

---

## Contact

For QC-related questions:
- **GitHub Issues**: [https://github.com/shuozhou87/QuantDSF/issues](https://github.com/shuozhou87/QuantDSF/issues)

---

**Document End**
