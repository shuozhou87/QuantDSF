#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Curve Plot Components
======================
曲线绑图组件
"""

import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional


def create_curve_plot(
    curves: List[Dict[str, Any]],
    title: str = "Melting Curves",
    x_label: str = "Temperature (°C)",
    y_label: str = "Fluorescence (AU)"
) -> go.Figure:
    """
    创建曲线图
    
    Args:
        curves: 曲线数据列表，每个包含 T, F, name, color（可选）
        title: 图表标题
        x_label: X 轴标签
        y_label: Y 轴标签
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    colors = px.colors.qualitative.Plotly
    
    for i, curve in enumerate(curves):
        color = curve.get('color', colors[i % len(colors)])
        
        fig.add_trace(go.Scatter(
            x=curve['T'],
            y=curve['F'],
            mode='lines',
            name=curve.get('name', f'Curve {i+1}'),
            line=dict(color=color, width=2),
            hovertemplate=f"T: %{{x:.1f}}°C<br>F: %{{y:.1f}}<extra>{curve.get('name', '')}</extra>"
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=0.99,
            xanchor='left',
            x=1.02
        ),
        margin=dict(l=60, r=120, t=50, b=60)
    )
    
    return fig


def create_overlay_plot(
    curves: List[Dict[str, Any]],
    selected_indices: List[int] = None,
    title: str = "Overlay Curves"
) -> go.Figure:
    """
    创建叠加曲线图（带选择状态）
    
    Args:
        curves: 曲线数据列表
        selected_indices: 选中的曲线索引
        title: 图表标题
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    if selected_indices is None:
        selected_indices = list(range(len(curves)))
    
    # 使用 Viridis 色谱
    colors = px.colors.sample_colorscale('Viridis', len(curves))
    
    for i, curve in enumerate(curves):
        is_selected = i in selected_indices
        
        fig.add_trace(go.Scatter(
            x=curve['T'],
            y=curve['progress'],
            mode='lines',
            name=f"{'✓' if is_selected else '✗'} {curve.get('name', '')}",
            line=dict(
                color=colors[i],
                width=3 if is_selected else 1,
                dash='solid' if is_selected else 'dot'
            ),
            opacity=0.9 if is_selected else 0.3
        ))
    
    fig.update_layout(
        title=f"{title}<br><sub>✓ = Selected | ✗ = Excluded</sub>",
        xaxis_title="Temperature (°C)",
        yaxis_title="Progress (%)",
        template='plotly_white',
        hovermode='closest',
        yaxis=dict(range=[-5, 105])
    )
    
    return fig


def create_vanthoff_plot(
    inv_T: np.ndarray,
    ln_kd: np.ndarray,
    fit_slope: float,
    fit_intercept: float,
    kd_298k: float,
    kd_310k: float,
    r_squared: float
) -> go.Figure:
    """
    创建 Van't Hoff 图
    
    Args:
        inv_T: 1/T 数组 (K⁻¹)
        ln_kd: ln(KD) 数组
        fit_slope: 拟合斜率
        fit_intercept: 拟合截距
        kd_298k: 298K 时的 KD
        kd_310k: 310K 时的 KD
        r_squared: R²
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    # 数据点
    fig.add_trace(go.Scatter(
        x=inv_T * 1000,  # 显示为 1000/T
        y=ln_kd,
        mode='markers',
        name='Data',
        marker=dict(size=10, color='#2c3e50')
    ))
    
    # 拟合线
    x_fit = np.linspace(inv_T.min() * 0.98, inv_T.max() * 1.02, 100)
    y_fit = fit_slope * x_fit + fit_intercept
    
    fig.add_trace(go.Scatter(
        x=x_fit * 1000,
        y=y_fit,
        mode='lines',
        name=f'Linear Fit (R²={r_squared:.3f})',
        line=dict(color='#e74c3c', width=2)
    ))
    
    # 外推点
    inv_298 = 1.0 / 298.15
    inv_310 = 1.0 / 310.15
    
    fig.add_trace(go.Scatter(
        x=[inv_298 * 1000, inv_310 * 1000],
        y=[np.log(kd_298k), np.log(kd_310k)],
        mode='markers',
        name='Extrapolated (298K, 310K)',
        marker=dict(size=14, color='#27ae60', symbol='star')
    ))
    
    fig.update_layout(
        title="Van't Hoff Plot",
        xaxis_title="1000/T (K⁻¹)",
        yaxis_title="ln(KD)",
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(l=60, r=30, t=80, b=60)
    )
    
    return fig


def create_isothermal_panels(
    T_grid: np.ndarray,
    concentrations: np.ndarray,
    Y_folded: np.ndarray,
    ec50_data: List[Dict],
    n_panels: int = 6
) -> go.Figure:
    """
    创建等温剂量响应面板图
    
    Args:
        T_grid: 温度网格
        concentrations: 浓度数组
        Y_folded: 折叠分数矩阵
        ec50_data: EC50 数据列表
        n_panels: 面板数量
    
    Returns:
        Plotly Figure
    """
    # 选择代表性温度
    n_panels = min(n_panels, len(ec50_data))
    idx_sel = np.linspace(0, len(ec50_data) - 1, n_panels, dtype=int)
    
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[f"T = {ec50_data[i]['temperature']:.1f}°C" for i in idx_sel]
    )
    
    for plot_idx, ec50_idx in enumerate(idx_sel):
        row = plot_idx // 3 + 1
        col = plot_idx % 3 + 1
        
        ec50 = ec50_data[ec50_idx]
        T_idx = np.argmin(np.abs(T_grid - ec50['temperature']))
        y_data = Y_folded[:, T_idx]
        
        # 数据点
        fig.add_trace(
            go.Scatter(
                x=concentrations,
                y=y_data,
                mode='markers',
                marker=dict(size=6, color='gray'),
                showlegend=False
            ),
            row=row, col=col
        )
        
        # 4PL 拟合曲线
        x_dense = np.logspace(
            np.log10(concentrations.min()),
            np.log10(concentrations.max()),
            100
        )
        log_ec50 = np.log10(ec50['ec50'])
        y_dense = ec50['bottom'] + (ec50['top'] - ec50['bottom']) / \
                  (1.0 + 10.0 ** (ec50['hill_slope'] * (log_ec50 - np.log10(x_dense))))
        
        fig.add_trace(
            go.Scatter(
                x=x_dense,
                y=y_dense,
                mode='lines',
                line=dict(color='blue', width=2),
                showlegend=False
            ),
            row=row, col=col
        )
        
        fig.update_xaxes(type='log', row=row, col=col)
        fig.update_yaxes(range=[-5, 105], row=row, col=col)
    
    fig.update_layout(
        title_text="Isothermal Dose-Response Fits",
        height=500,
        showlegend=False
    )
    
    return fig


