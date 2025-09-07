#!/usr/bin/env python3
"""
nanoDSF Tm Calculation & Screening Streamlit App (Updated SL-0422.py)
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
st.set_page_config(page_title="nanoDSF Tₘ Calculator & Screening", layout="wide")
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
uploaded = st.file_uploader("Upload nanoDSF ZIP archive", type="zip")
if not uploaded:
    st.info("Please upload a ZIP file containing raw CSV files.")
    st.stop()

# Helper: first derivative method with automatic SG window and secondary smoothing
def calc_tm_derivative(T, F):
    # Estimate temperature step size
    steps = np.diff(T)
    step = np.median(steps)
    # Desired transition span ~5°C -> window points
    win_pts = int(round(5.0 / step))
    # Ensure odd and minimum
    if win_pts < 5:
        win_pts = 5
    if win_pts % 2 == 0:
        win_pts += 1
    # Bound max
    if win_pts > len(F) - 1:
        win_pts = len(F) - 2 if (len(F)-1)%2==1 else len(F) - 1
    # Primary smoothing
    smooth = savgol_filter(F, window_length=win_pts, polyorder=3)
    # Derivative
    deriv = np.gradient(smooth, T)
    # Secondary smoothing
    deriv = savgol_filter(deriv, window_length=win_pts, polyorder=3)
    # Find peak
    idx = np.argmax(deriv[10:-10]) + 10
    return T[idx], smooth, deriv

# Helper: two-state Boltzmann regression

def calc_tm_boltzmann(T, F):
    # initial guesses
    p0 = [
        F[0] - F.min(), 0.01, F.min(),
        F.max() - F.min(), 0.005, F.min(),
        np.median(T), 2.0
    ]
    try:
        popt, pcov = curve_fit(boltzmann_exp, T, F, p0=p0, maxfev=20000)
    except RuntimeError:
        return np.nan, (np.nan, np.nan), np.nan, np.nan, np.nan, None, None
    # extract
    Tm = popt[6]
    se = np.sqrt(np.diag(pcov))[6]
    dfree = len(T) - len(popt)
    tval = t.ppf(0.975, dfree)
    ci = (Tm - tval*se, Tm + tval*se)
    # goodness
    ypred = boltzmann_exp(T, *popt)
    resid = F - ypred
    ss_res = np.sum(resid**2)
    ss_tot = np.sum((F - F.mean())**2)
    r2 = 1 - ss_res/ss_tot
    # SNR
    folded = F[:10].mean()
    unfolded = F[-10:].mean()
    snr = abs(unfolded-folded)/np.std(resid)
    return Tm, ci, se, snr, r2, popt, pcov

# Process data
results = []
cap_data = {}
with zipfile.ZipFile(uploaded, "r") as z:
    # find any raw CSV files under subdirs
    all_files = z.namelist()
    csvs = sorted([f for f in all_files if f.lower().endswith("raw.csv")])
    if not csvs:
        st.error("No raw CSV files found in the ZIP archive.")
        st.stop()
    for csv_path in csvs:
        # label by filename
        rep = os.path.splitext(os.path.basename(csv_path))[0]
        # channel filter
        if channel.startswith("350/330") and 'ratio' not in csv_path.lower(): continue
        if channel == '350 nm' and '350 nm' not in csv_path.lower(): continue
        if channel == '330 nm' and '330 nm' not in csv_path.lower(): continue
        raw = z.read(csv_path)
        df = pd.read_csv(io.BytesIO(raw), sep='\t')
        df.columns = [c.strip() for c in df.columns]
        T = df['T[°C]'].values
        F = df[df.columns[1]].values
        # compute
        if method.startswith("First derivative"):
            Tm, smooth, deriv = calc_tm_derivative(T, F)
            idx = np.argmax(deriv[10:-10]) + 10
            base = np.concatenate([deriv[10:30], deriv[-30:-10]])
            snr = (deriv[idx] - base.mean()) / base.std() if base.std() else np.nan
            ci_low = ci_high = se = r2 = np.nan
            cap_data[rep] = {'T':T,'F':F,'smooth':smooth,'deriv':deriv}
        else:
            Tm, (ci_low,ci_high), se, snr, r2, popt, pcov = calc_tm_boltzmann(T, F)
            cap_data[rep] = {'T':T,'F':F,'popt':popt}
        results.append({
            'Capillary': rep,
            'Tₘ (°C)': Tm,
            'CI Lower': ci_low,
            'CI Upper': ci_high,
            'SE (°C)': se,
            'SNR': snr,
            'R²': r2,
            'Sample Info': '',
            'Concentration': ''
        })

# Summary table
st.header("Summary of Tₘ Results")
_df = pd.DataFrame(results)
# no integer cast, leave Capillary as string
try:
    _df = _df.sort_values('Capillary')
except:
    pass

df_res = _df.reset_index(drop=True)
edited = st.data_editor(
    df_res,
    key='editor',
    hide_index=True,
    use_container_width=True
)
st.info("Fill 'Sample Info' and 'Concentration', then run EC₅₀ or ΔTₘ.")

# EC50 fitting
if st.button("Calculate EC₅₀"):
    df_fit = edited.dropna(subset=['Concentration'])
    x = df_fit['Concentration'].astype(float).values
    y = df_fit['Tₘ (°C)'].values
    errs = df_fit['SE (°C)'].astype(float).values
    def hill4(x,b,t,ec,n): return b + (t-b)*x**n/(ec**n+x**n)
    p0 = [y.min(), y.max(), np.median(x), 1.0]
    popt, pcov = curve_fit(hill4, x, y, p0=p0, maxfev=100000)
    ec50 = popt[2]; se_ec = np.sqrt(pcov[2,2])
    dfree = len(x)-len(popt); tval = t.ppf(0.975, dfree)
    ci = (ec50-tval*se_ec, ec50+tval*se_ec)
    st.subheader("Dose–Response Fit Results")
    st.write(f"EC₅₀ = {ec50:.2e} M (95% CI: {ci[0]:.2e}–{ci[1]:.2e})")
    fig, ax = plt.subplots()
    ax.errorbar(x, y, yerr=errs, fmt='o', label='Data ± SE')
    xs = np.logspace(np.log10(x.min()/2), np.log10(x.max()*2), 200)
    ax.semilogx(xs, hill4(xs,*popt), '-', label=f'Fit EC₅₀={ec50:.2e} M')
    ax.set_xlabel('Concentration (M)'); ax.set_ylabel('Tₘ (°C)'); ax.legend()
    st.pyplot(fig)

# Single-dose ΔTₘ screening
st.header("Single-Dose ΔTₘ Screening")
cap_options = df_res['Capillary'].tolist()
control = st.selectbox("Select control capillary", cap_options)
tests = st.multiselect("Select test capillaries", [c for c in cap_options if c!=control])
if st.button("Calculate ΔTₘ"):
    t0 = df_res.loc[df_res['Capillary']==control,'Tₘ (°C)'].values[0]
    s0 = df_res.loc[df_res['Capillary']==control,'SE (°C)'].values[0]
    rows=[]
    for c in tests:
        tm = df_res.loc[df_res['Capillary']==c,'Tₘ (°C)'].values[0]
        se = df_res.loc[df_res['Capillary']==c,'SE (°C)'].values[0]
        d = tm - t0; se_d=np.sqrt(se**2+s0**2)
        info = edited.loc[edited['Capillary']==c,'Sample Info'].values[0] if 'Sample Info' in edited.columns else ''
        rows.append({'Capillary':c,'Sample Info':info,'ΔTₘ (°C)':d,'SE ΔTₘ':se_d})
    df_delta = pd.DataFrame(rows).sort_values('ΔTₘ (°C)',ascending=False)
    st.dataframe(df_delta,use_container_width=True)
    fig, ax = plt.subplots()
    ax.bar(df_delta['Sample Info'], df_delta['ΔTₘ (°C)'], yerr=df_delta['SE ΔTₘ'])
    ax.set_ylabel('ΔTₘ (°C)')
    ax.set_xticklabels(df_delta['Sample Info'], rotation=45, ha='right')
    st.pyplot(fig)

# Detailed per-capillary plots
st.info("Click on a capillary to view detailed curves.")
for rep, data in cap_data.items():
    with st.expander(f"Capillary {rep}"):
        T = data['T']; F = data['F']
        if method.startswith('First derivative'):
            smooth = data['smooth']; deriv = data['deriv']
            fig1, ax1 = plt.subplots(); ax1.plot(T,F,label='Raw'); ax1.plot(T,smooth,label='Smoothed')
            ax1.set_xlabel('T (°C)'); ax1.set_ylabel('Fluorescence'); ax1.legend(); st.pyplot(fig1)
            fig2, ax2 = plt.subplots(); ax2.plot(T[10:-10],deriv[10:-10],label='dF/dT')
            tm_val = df_res.loc[df_res['Capillary']==rep,'Tₘ (°C)'].values
            if tm_val.size: ax2.axvline(tm_val[0],color='red',linestyle='--')
            ax2.set_xlabel('T (°C)'); ax2.set_ylabel('dF/dT'); ax2.legend(); st.pyplot(fig2)
        else:
            popt = data.get('popt')
            fig3, ax3 = plt.subplots(); ax3.plot(T,F,'.',label='Raw')
            if popt is not None:
                ax3.plot(T,boltzmann_exp(T,*popt),'-',label='Fit')
                tm_val = df_res.loc[df_res['Capillary']==rep,'Tₘ (°C)'].values
                if tm_val.size: ax3.axvline(tm_val[0],color='red',linestyle='--')
            ax3.set_xlabel('T (°C)'); ax3.set_ylabel('Fluorescence'); ax3.legend(); st.pyplot(fig3)

st.success("Analysis complete.")
