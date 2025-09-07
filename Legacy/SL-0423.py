#!/usr/bin/env python3
"""
nanoDSF Tm Calculation & Screening Streamlit App
"""
import sys
import os

# Avoid naming conflict if script name matches module
curdir = os.path.dirname(__file__)
if curdir in sys.path:
    sys.path.remove(curdir)

import streamlit as st
# Restore path
sys.path.insert(0, curdir)

import zipfile
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit
from scipy.stats import t

# Global Boltzmann function for fitting and plotting
def boltzmann_exp(T, A_N, alpha, D_N, A_D, beta, D_D, Tm, k):
    F_N = A_N * np.exp(-alpha * T) + D_N
    F_D = A_D * np.exp(-beta * T) + D_D
    return F_N + (F_D - F_N) / (1 + np.exp((Tm - T) / k))

# Page configuration
st.set_page_config(
    page_title="nanoDSF Tₘ Calculator & Screening", layout="wide"
)
st.title("nanoDSF Tₘ Calculation & Screening App")

# Sidebar settings
st.sidebar.header("Analysis Settings")
method = st.sidebar.selectbox(
    "Select Tₘ calculation method:",
    ["Two-state Boltzmann (default)", "First derivative"]
)
channel = st.sidebar.selectbox(
    "Select data channel:",
    ["350/330 nm ratio (default)", "350 nm", "330 nm"]
)
if method.startswith("First derivative"):
    window = st.sidebar.number_input(
        "Savitzky–Golay window length:",
        min_value=5,
        max_value=101,
        step=2,
        value=21,
    )

# Upload data ZIP
uploaded = st.file_uploader(
    "Upload nanoDSF ZIP archive", type="zip"
)
if not uploaded:
    st.info("Please upload a ZIP file containing '_unfolding_raw.csv' files.")
    st.stop()

# Helper: first derivative method
def calc_tm_derivative(T, F, window_length):
    smooth = savgol_filter(F, window_length=window_length, polyorder=3)
    deriv = np.gradient(smooth, T)
    idx = np.argmax(deriv[10:-10]) + 10
    return T[idx], smooth, deriv

# Helper: two-state Boltzmann fit via global boltzmann_exp
def calc_tm_boltzmann(T, F):
    # initial parameter guesses
    p0 = [
        F[0] - F.min(),
        0.01,
        F.min(),
        F.max() - F.min(),
        0.005,
        F.min(),
        np.median(T),
        2.0,
    ]
    try:
        popt, pcov = curve_fit(
            boltzmann_exp, T, F, p0=p0, maxfev=20000
        )
    except RuntimeError:
        return np.nan, (np.nan, np.nan), np.nan, np.nan, np.nan, None, None

    # extract fitted parameters
    Tm = popt[6]
    se = np.sqrt(np.diag(pcov))[6]
    dfree = len(T) - len(popt)
    tval = t.ppf(0.975, dfree)
    ci = (Tm - tval * se, Tm + tval * se)

    # predicted and residuals
    y_pred = boltzmann_exp(T, *popt)
    resid = F - y_pred
    ss_res = np.sum(resid**2)
    ss_tot = np.sum((F - F.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot

    # signal-to-noise
    folded = F[:10].mean()
    unfolded = F[-10:].mean()
    snr = abs(unfolded - folded) / np.std(resid)

    return Tm, ci, se, snr, r2, popt, pcov

# Process data
results = []
cap_data = {}

with zipfile.ZipFile(uploaded, "r") as z:
    # Recursively gather replicate-level raw CSVs
    file_list = z.namelist()
    files = sorted([f for f in file_list if '/Replicate ' in f and f.endswith('_unfolding_raw.csv')])
    for path in files:
        # Parse condition and replicate from path
        parts = path.split('/')
        # parts[1] = condition folder, parts[2] = 'Replicate N'
        condition = parts[1]
        repdir = parts[2]
        repnum = repdir.split(' ')[1]
        rep_label = f"{condition} (rep {repnum})"
        # Filter by channel
        if channel.startswith('350/330') and 'Ratio' not in path:
            continue
        if channel == '350 nm' and ('350 nm' not in path or 'Ratio' in path):
            continue
        if channel == '330 nm' and ('330 nm' not in path or 'Ratio' in path):
            continue
        # Load CSV data
        raw = z.read(path)
        df = pd.read_csv(io.BytesIO(raw), sep='	')
        df.columns = [c.strip() for c in df.columns]
        T = df['T[°C]'].values
        F = df[df.columns[1]].values
        # Compute metrics
        if method.startswith('First derivative'):
            Tm, smooth, deriv = calc_tm_derivative(T, F, window)
            idx = np.argmax(deriv[10:-10]) + 10
            base = np.concatenate([deriv[10:30], deriv[-30:-10]])
            snr = (deriv[idx] - base.mean()) / base.std() if base.std() else np.nan
            ci_low = ci_high = se = r2 = np.nan
            cap_data[rep_label] = {'T': T, 'F': F, 'smooth': smooth, 'deriv': deriv}
        else:
            Tm, (ci_low, ci_high), se, snr, r2, popt, pcov = calc_tm_boltzmann(T, F)
            cap_data[rep_label] = {'T': T, 'F': F, 'popt': popt}
        results.append({
            'Capillary': rep_label,
            'Tₘ (°C)': Tm,
            'CI Lower': ci_low,
            'CI Upper': ci_high,
            'SE (°C)': se,
            'SNR': snr,
            'R²': r2,
            'Sample Info': '',
            'Concentration': ''
        })

# display summary table
st.header("Summary of Tₘ Results")

df_res = (
    pd.DataFrame(results)
    .sort_values("Capillary")
    .reset_index(drop=True)
)
edited = st.data_editor(
    df_res,
    key="editor",
    hide_index=True,
    use_container_width=True,
)  # user fills Sample Info, Concentration

st.info(
    "Fill 'Sample Info' and 'Concentration', then click buttons below."
)

# EC50 button
if st.button("Calculate EC₅₀"):
    df_fit = edited.dropna(subset=["Concentration"])
    x = df_fit["Concentration"].astype(float).values
    y = df_fit["Tₘ (°C)"].values
    errs = df_fit["SE (°C)"].astype(float).values

    def hill4(x, b, t, ec, n):
        return b + (t - b) * x**n / (ec**n + x**n)

    p0 = [y.min(), y.max(), np.median(x), 1.0]
    popt, pcov = curve_fit(
        hill4, x, y, p0=p0, maxfev=100000
    )
    ec50 = popt[2]
    se_ec = np.sqrt(pcov[2, 2])
    dfree = len(x) - len(popt)
    tval = t.ppf(0.975, dfree)
    ci = (ec50 - tval * se_ec, ec50 + tval * se_ec)

    st.subheader("Dose–Response Fit Results")
    st.write(
        f"EC₅₀ = {ec50:.2e} M (95% CI: {ci[0]:.2e}–{ci[1]:.2e})"
    )
    fig, ax = plt.subplots()
    ax.errorbar(x, y, yerr=errs, fmt="o", label="Data ± SE")
    xs = np.logspace(
        np.log10(x.min() / 2), np.log10(x.max() * 2), 200
    )
    ax.semilogx(
        xs, hill4(xs, *popt),
        label=f"Fit EC₅₀={ec50:.2e} M"
    )
    ax.set_xlabel("Concentration (M)")
    ax.set_ylabel("Tₘ (°C)")
    ax.legend()
    st.pyplot(fig)

# single-dose screening
st.header("Single-Dose ΔTₘ Screening")
control = st.selectbox(
    "Select control capillary", edited["Capillary"]
)
tests = st.multiselect(
    "Select test capillaries", [c for c in edited["Capillary"] if c != control]
)
if st.button("Calculate ΔTₘ"):
    t0 = edited.loc[
        edited["Capillary"] == control, "Tₘ (°C)"
    ].values[0]
    s0 = edited.loc[
        edited["Capillary"] == control, "SE (°C)"
    ].values[0]
    rows = []
    for c in tests:
        tm = edited.loc[
            edited["Capillary"] == c, "Tₘ (°C)"
        ].values[0]
        se = edited.loc[
            edited["Capillary"] == c, "SE (°C)"
        ].values[0]
        d = tm - t0
        se_d = np.sqrt(se**2 + s0**2)
        info = edited.loc[
            edited["Capillary"] == c, "Sample Info"
        ].values[0]
        rows.append({
            "Capillary": c,
            "Sample Info": info,
            "ΔTₘ (°C)": d,
            "SE ΔTₘ": se_d,
        })
    df_delta = pd.DataFrame(rows).sort_values(
        "ΔTₘ (°C)", ascending=False
    )
    st.dataframe(df_delta, use_container_width=True)
    fig, ax = plt.subplots()
    ax.bar(
        df_delta["Sample Info"],
        df_delta["ΔTₘ (°C)"],
        yerr=df_delta["SE ΔTₘ"],
    )
    ax.set_ylabel("ΔTₘ (°C)")
    ax.set_xticklabels(
        df_delta["Sample Info"], rotation=45, ha="right"
    )
    st.pyplot(fig)

# Detailed per-capillary plots
st.info("Click on a capillary below to view detailed raw/fitted curves.")
for rep_label, data in cap_data.items():
    with st.expander(f"Capillary {rep_label}"):
        T = data['T']
        F = data['F']
        if method.startswith('First derivative'):
            smooth = data['smooth']
            deriv = data['deriv']
            # Raw and smoothed
            fig1, ax1 = plt.subplots()
            ax1.plot(T, F, label='Raw')
            ax1.plot(T, smooth, label='Smoothed')
            ax1.set_xlabel('Temperature (°C)')
            ax1.set_ylabel('Fluorescence')
            ax1.legend()
            st.pyplot(fig1)
            # Derivative
            T_trim = T[10:-10]
            deriv_trim = deriv[10:-10]
            fig2, ax2 = plt.subplots()
            ax2.plot(T_trim, deriv_trim, label='dF/dT (trimmed)')
            tm_val = edited.loc[edited['Capillary']==rep_label, 'Tₘ (°C)'].values
            if tm_val.size:
                ax2.axvline(tm_val[0], color='red', linestyle='--')
            ax2.set_xlabel('Temperature (°C)')
            ax2.set_ylabel('Derivative')
            ax2.legend()
            st.pyplot(fig2)
        else:
            popt = data.get('popt')
            fig3, ax3 = plt.subplots()
            ax3.plot(T, F, '.', label='Raw')
            if popt is not None:
                ax3.plot(T, boltzmann_exp(T, *popt), '-', label='Boltzmann fit')
                tm_val = edited.loc[edited['Capillary']==rep_label, 'Tₘ (°C)'].values
                if tm_val.size:
                    ax3.axvline(tm_val[0], color='red', linestyle='--')
            ax3.set_xlabel('Temperature (°C)')
            ax3.set_ylabel('Fluorescence')
            ax3.legend()
            st.pyplot(fig3)

st.success("Analysis complete.")
