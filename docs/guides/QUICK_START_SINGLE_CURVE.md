# Single-Curve Thermodynamics - Quick Start Guide

## What is it?

Extract thermodynamic parameters (ΔG°, ΔH°, ΔS°) from **single DSF curves** without needing concentration series data.

Based on: Wright et al. 2017, *J. Phys. Chem. Lett.* 8, 553-558

## When to use?

✅ **Use Single-Curve when**:
- Single concentration per sample
- pH/buffer screening
- Mutant comparisons
- Formulation optimization

❌ **Use Isothermal Slicing when**:
- Concentration series available
- Ligand binding studies (Kd measurement)
- Detailed concentration-dependent analysis

## How to use (3 steps)

### Step 1: Upload your nanoDSF data
- Standard ZIP format from Prometheus/Uncle
- Single or multiple samples

### Step 2: Select method
1. Click **Advanced Settings** (⚙️ icon in left sidebar)
2. Under "Thermodynamic Analysis Method", select:
   - **Single-Curve Method (Wright 2017)** ← Select this!
   - Default is "Isothermal Slicing (Van't Hoff)"

### Step 3: Run analysis
- Choose Tm method: **AUC** or **TSB** (recommended)
  - Note: FD may not provide reliable progress curves
- Click **Run Analysis**

## Understanding results

New columns will appear in the results table:

| Column | Meaning | Typical Range |
|--------|---------|---------------|
| **ΔG° (kJ/mol)** | Free energy at 25°C | 10-150 |
| **ΔH° (kJ/mol)** | Enthalpy change | 50-1000 |
| **ΔS° (J/mol·K)** | Entropy change | 200-3000 |
| **Thermo R²** | Fit quality | >0.90 good |
| **Thermo** | Quality flag | ✓/⚠️/-- |

### Quality flags:
- **✓** (green): High quality (R²>0.90, physically reasonable)
- **⚠️** (yellow): Acceptable but with warnings
- **--** (gray): Analysis failed or not run

## Example workflow

```
1. Upload: protein_screening_pH.zip
2. Settings: Advanced Settings → Single-Curve Method
3. Tm method: AUC
4. Run Analysis
5. Review: Check "Thermo R²" column (should be >0.90)
6. Compare: ΔG° values across pH conditions
```

## Troubleshooting

### Q: Why are some thermodynamic parameters "N/A"?

**Common reasons**:
- Tm calculation failed (check Status column)
- R² < 0.90 (poor linearity)
- Insufficient data points in 10-50% unfolding region
- Using FD method (provides no progress curve)

**Solutions**:
- Use AUC or TSB method (not FD)
- Check data quality (SNR, R²)
- Verify temperature range covers transition

### Q: R² is low (<0.90), what does it mean?

**Possible causes**:
- Multi-state unfolding (not simple two-state)
- Aggregation during unfolding
- Noisy data
- Non-equilibrium effects

**Action**: Results may still be useful for relative comparisons, but absolute values less reliable.

## Validation

Our implementation has been validated against Wright et al. 2017 literature values:

| Protein | ΔG° Error | ΔH° Error | ΔS° Error | R² |
|---------|-----------|-----------|-----------|-----|
| Lysozyme | 3.3% | 3.4% | 3.3% | 0.9987 |
| Carbonic Anhydrase | 5.0% | 4.8% | 5.1% | 0.9994 |
| Chymotrypsin | 1.8% | 1.9% | 1.7% | 0.9995 |
| Peroxidase | 3.6% | 3.5% | 3.7% | 0.9994 |

All errors <6%, R² >0.998 ✅

## Key assumptions and limitations

⚠️ **Assumptions**:
1. Two-state unfolding (folded ↔ unfolded)
2. Reversible transition (actually nanoDSF is often irreversible)
3. Negligible ΔCp (heat capacity change)

💡 **Best practice**: Use for **relative comparisons** between samples rather than absolute thermodynamic values.

## More information

- [Full methodology](SINGLE_CURVE_THERMODYNAMICS.md)
- [Integration details](SINGLE_CURVE_INTEGRATION.md)
- [Original paper](../manuscript/ref/extraction-of-thermodynamic-parameters-of-protein-unfolding-using-parallelized-differential-scanning-fluorimetry.pdf)

---

**Feature status**: ✅ Production ready (v2.0)
**Last updated**: 2025-12-15
