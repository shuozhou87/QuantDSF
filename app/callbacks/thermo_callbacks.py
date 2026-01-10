#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thermodynamic Analysis Callbacks
=================================
热力学分析相关回调
"""

from dash import Dash, callback, Input, Output, State, html, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
import re
from typing import List
from core.analysis.thermodynamic.ec50_kd import convert_ec50_to_kd
from core.qc import ThermodynamicQualityController
from core.qc.config import QCSettings


def register_thermo_callbacks(app: Dash) -> None:
    """注册热力学分析相关回调"""

    def _format_kd(kd_molar: float) -> str:
        """自适应 KD 单位格式化"""
        if kd_molar is None or not np.isfinite(kd_molar) or kd_molar <= 0:
            return "--"
        if kd_molar >= 1e-3:
            return f"{kd_molar*1e3:.2f} mM"
        if kd_molar >= 1e-6:
            return f"{kd_molar*1e6:.2f} µM"
        if kd_molar >= 1e-9:
            return f"{kd_molar*1e9:.2f} nM"
        if kd_molar >= 1e-12:
            return f"{kd_molar*1e12:.2f} pM"
        return f"{kd_molar:.2e} M"
    
    def _parse_protein_conc_to_m(value) -> float:
        """
        将用户输入的蛋白浓度转换为 M。
        支持纯数值（默认视为 M；但若值很大则按 nM 解释）和带单位字符串（nM/µM/mM/M）。
        """
        if value is None:
            return None
        # 字符串解析，支持 nm/um/µm/mm/m
        if isinstance(value, str):
            s = value.strip().lower().replace("µ", "u")
            m = re.match(r"([0-9.+-eE]+)\s*(nm|um|mm|m)?", s)
            if not m:
                return None
            num = float(m.group(1))
            unit = m.group(2)
            if unit == "nm":
                return num * 1e-9
            if unit == "um":
                return num * 1e-6
            if unit == "mm":
                return num * 1e-3
            # 默认 M
            return num
        # 数值输入：若数值过大，推测为 nM；否则按 M
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        if num > 1e-2:  # 0.01 M 已很高，通常用户输入的“大数”是 nM
            return num * 1e-9
        return num

    def _parse_conc_to_m(val):
        """
        解析浓度字符串到 M，支持 pm/nm/µm/mM/M，或直接数值。
        """
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            s = val.strip().lower().replace("µ", "u")
            m = re.match(r"([0-9.+-eE]+)\s*(pm|nm|um|mm|m)?", s)
            if not m:
                return None
            num = float(m.group(1))
            unit = m.group(2)
            if unit == "pm":
                return num * 1e-12
            if unit == "nm":
                return num * 1e-9
            if unit == "um":
                return num * 1e-6
            if unit == "mm":
                return num * 1e-3
            return num
        return None
    
    # Note: thermo-analysis-content is rendered by tab_callbacks.py
    # This file handles specific thermodynamic analysis interactions

    @app.callback(
        Output('vh-selection-table', 'data'),
        Output('vh-selection-table', 'selected_rows'),
        Output('vh-selection-hint', 'children'),
        Output('vh-temp-slice-range', 'min'),
        Output('vh-temp-slice-range', 'max'),
        Output('vh-temp-slice-range', 'value'),
        Output('vh-temp-slice-range', 'marks'),
        Output('vh-temp-range-label', 'children'),
        Input('analysis-results-store', 'data'),
        Input('main-tabs', 'active_tab'),
    )
    def populate_vh_table(results_data, active_tab):
        """填充 Van't Hoff 选择表，并自动选择高质量数据"""
        # 仅在热力学标签页时更新；其他标签保持不变
        if active_tab != 'thermo':
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        if not results_data or not results_data.get('results'):
            default_marks = {x: str(x) for x in range(20, 101, 10)}
            return [], [], "No analysis data. Run Tm analysis first.", 20, 100, [30, 80], default_marks, ""
        
        # 收集所有行数据,附带原始浓度值用于排序
        rows_with_meta = []
        results = results_data['results']
        t_values = []

        for idx, r in enumerate(results):
            tm = r.get('tm')
            r2 = r.get('r_squared')
            conc = r.get('concentration')
            conc_nM = conc * 1e9 if conc is not None else None

            rows_with_meta.append({
                "idx": idx,  # 原始results索引,保持不变
                "name": r.get('name'),
                "conc_nM": f"{conc_nM:.2f}" if conc_nM is not None else "N/A",
                "tm": f"{tm:.1f}" if tm is not None else "N/A",
                "r2": f"{r2:.3f}" if r2 is not None else "N/A",
                "method": r.get('method', '').upper(),
                "quality": r.get('quality_flag', ''),
                "_conc_sort": conc if conc is not None and np.isfinite(conc) else float('inf'),  # 排序键
                "_r2_val": r2  # 用于自动选择
            })
            if tm is not None:
                t_values.append(tm)

        # 按浓度从低到高排序(无效浓度排到最后)
        rows_with_meta.sort(key=lambda x: x['_conc_sort'])

        # 生成最终表格数据和自动选择索引
        rows = []
        auto_selected = []

        for table_row_idx, row_meta in enumerate(rows_with_meta):
            # 构建表格行(包含隐藏的原始idx字段)
            rows.append({
                "idx": row_meta['idx'],  # 保留原始索引,overlay图需要用
                "name": row_meta['name'],
                "conc_nM": row_meta['conc_nM'],
                "tm": row_meta['tm'],
                "r2": row_meta['r2'],
                "method": row_meta['method'],
                "quality": row_meta['quality']
            })

            # 自动选择R²≥0.9的行(使用表格行索引)
            if row_meta['_r2_val'] is not None and row_meta['_r2_val'] >= 0.9:
                auto_selected.append(table_row_idx)
        
        hint = f"{len(rows)} total; auto-selected {len(auto_selected)} rows with R² ≥ 0.9. Adjust selection as needed."
        if t_values:
            t_min = float(min(t_values))
            t_max = float(max(t_values))
            span = max(t_max - t_min, 5)
            slider_min = max(0, t_min - 2)
            slider_max = t_max + 2
            default_range = [t_min, t_max]
            label = f"Temperature window: {t_min:.1f}–{t_max:.1f} °C"
            # 生成可读刻度，每隔5°C
            mark_start = int(np.floor(slider_min / 5) * 5)
            mark_end = int(np.ceil(slider_max / 5) * 5)
            marks = {x: str(x) for x in range(mark_start, mark_end + 1, 5)}
        else:
            slider_min, slider_max, default_range, label = 20, 100, [30, 80], ""
            marks = {x: str(x) for x in range(20, 101, 10)}
        return rows, auto_selected, hint, slider_min, slider_max, default_range, marks, label
    
    @app.callback(
        Output('vanthoff-plot', 'figure'),
        Output('vh-delta-h', 'children'),
        Output('vh-delta-s', 'children'),
        Output('vh-kd-298', 'children'),
        Output('vh-kd-310', 'children'),
        Output('vh-r2', 'children'),
        Input('run-vanthoff-btn', 'n_clicks'),
        State('protein-conc-input', 'value'),
        State('vh-method-selector', 'value'),
        State('units-selector', 'value'),
        State('vh-temp-slice-range', 'value'),
        State('analysis-results-store', 'data'),
        State('vh-selection-table', 'selected_rows'),
        State('vh-selection-table', 'data'),
        State('isothermal-ec50-table', 'data'),
        prevent_initial_call=True
    )
    def run_vanthoff_analysis(n_clicks, protein_conc, method, units, temp_slice_range, results_data, selected_rows, table_data, iso_table_data):
        """运行 Van't Hoff 分析"""
        # 创建空图表
        fig = go.Figure()

        # 解析蛋白浓度（支持 M / nM / µM 输入）
        protein_conc = _parse_protein_conc_to_m(protein_conc)
        
        if not results_data or not results_data.get('results'):
            fig.add_annotation(
                text="No analysis data available. Run Tm analysis first.",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(template='plotly_white')
            return fig, "-- kJ/mol", "-- J/mol·K", "-- nM", "--", "--"
        
        # 优先使用等温 EC50/KD 表的数据进行 Van't Hoff（温度-EC50/KD 曲线）
        if iso_table_data:
            temperatures = []
            kd_vals = []
            for row in iso_table_data:
                t_val = row.get("temp")
                try:
                    t_f = float(t_val) if t_val not in (None, "N/A") else None
                except ValueError:
                    t_f = None
                kd_m = _parse_conc_to_m(row.get("kd")) or _parse_conc_to_m(row.get("ec50"))
                if t_f is not None and kd_m is not None and np.isfinite(kd_m) and kd_m > 0:
                    temperatures.append(t_f)
                    kd_vals.append(kd_m)
            temperatures_c = np.array(temperatures, dtype=float)
            kd_values = np.array(kd_vals, dtype=float)
        else:
            # 如果未生成等温表，则回退到样本 Tm-浓度数据（旧逻辑）
            if table_data:
                if not selected_rows:
                    fig.add_annotation(
                        text="Select at least 3 data points in the table for Van't Hoff analysis",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        showarrow=False,
                        font=dict(size=14, color="gray")
                    )
                    fig.update_layout(template='plotly_white')
                    return fig, "-- kJ/mol", "-- J/mol·K", "-- nM", "--", "--"
                selected = [table_data[i] for i in selected_rows if i < len(table_data)]
                valid_points = []
                for row in selected:
                    tm_val = row.get("tm")
                    try:
                        tm_f = float(tm_val) if tm_val not in (None, "N/A") else None
                    except ValueError:
                        tm_f = None
                    conc_val = row.get("conc_nM")
                    try:
                        conc_f = float(conc_val) * 1e-9 if conc_val not in (None, "N/A") else None
                    except ValueError:
                        conc_f = None
                    if tm_f is not None and conc_f is not None:
                        valid_points.append({"tm": tm_f, "concentration": conc_f})
            else:
                results = results_data['results']
                valid_points = [
                    r for r in results 
                    if r.get('concentration') and r.get('tm') is not None
                ]
            temperatures_c = np.array([r['tm'] for r in valid_points], dtype=float)
            kd_values = np.array([r['concentration'] for r in valid_points], dtype=float)
        
        if len(kd_values) < 3 or len(temperatures_c) < 3:
            fig.add_annotation(
                text=f"Need at least 3 data points for Van't Hoff (current: {len(kd_values)})",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(template='plotly_white')
            return fig, "-- kJ/mol", "-- J/mol·K", "-- nM", "--", "--"
        
        try:
            from core.analysis.thermodynamic import vanthoff
            from core.analysis.thermodynamic.ec50_kd import convert_ec50_to_kd
            
            # 准备数据：温度 (°C) 与 KD
            # 按温度排序
            sort_idx = np.argsort(temperatures_c)
            temperatures_c = temperatures_c[sort_idx]
            kd_values = kd_values[sort_idx]
            
            # 温度切片范围过滤
            if temp_slice_range and len(temp_slice_range) == 2:
                t_min, t_max = temp_slice_range
                mask_range = (temperatures_c >= t_min) & (temperatures_c <= t_max)
                temperatures_c = temperatures_c[mask_range]
                kd_values = kd_values[mask_range]

            # 基础数据质量检查
            mask_finite = np.isfinite(temperatures_c) & np.isfinite(kd_values) & (kd_values > 0)
            if mask_finite.sum() < 3:
                msg = f"Valid points after filtering: {mask_finite.sum()} (<3). Check KD/conc > 0 and finite Tm."
                fig.add_annotation(
                    text=msg,
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(size=14, color="red")
                )
                fig.update_layout(template='plotly_white')
                return fig, "Error", "Error", "Error", "--", "--"

            temperatures_c = temperatures_c[mask_finite]
            kd_values = kd_values[mask_finite]
            
            # 运行 Van't Hoff 分析（接受摄氏度）
            result = vanthoff.fit_vanthoff(temperatures_c, kd_values)
            
            if result and result.get('r2') is not None and np.isfinite(result.get('r2', np.nan)) and result.get('r2') >= 0:
                delta_h = result['deltaH']         # J/mol
                delta_s = result['deltaS']         # J/mol·K
                r2 = result['r2']
                
                # 单位转换
                target_units = "Calorie" if units == "calorie" else "Joule"
                delta_h_conv, delta_s_conv, _, _, delta_h_unit, delta_s_unit = vanthoff.convert_thermodynamic_units(
                    delta_h, delta_s, 0, 0, target_units
                )
                
                # 计算 298K (25°C) 时的 KD
                kd_298_raw = vanthoff.extrapolate_kd(result, 25.0)
                kd_310_raw = vanthoff.extrapolate_kd(result, 37.0)
                
                # 绘制 Van't Hoff 图
                temperatures_k = temperatures_c + 273.15
                inv_t = 1000 / temperatures_k  # 1000/T for better scale
                ln_kd = np.log(kd_values)
                
                # 数据点
                fig.add_trace(go.Scatter(
                    x=inv_t,
                    y=ln_kd,
                    mode='markers',
                    name='Data',
                    marker=dict(size=10, color='#3498db')
                ))
                
                # 拟合线
                inv_t_fit = np.linspace(min(inv_t), max(inv_t), 100)
                T_fit_kelvin = 1000 / inv_t_fit
                R = 8.314  # J/mol/K
                ln_kd_fit = (result['deltaH'] / R) * (1 / T_fit_kelvin) - (result['deltaS'] / R)
                
                fig.add_trace(go.Scatter(
                    x=inv_t_fit,
                    y=ln_kd_fit,
                    mode='lines',
                    name=f'Fit (R²={r2:.3f})',
                    line=dict(color='#e74c3c', dash='dash')
                ))
                
                fig.update_layout(
                    template='plotly_white',
                    xaxis_title='1000/T (K⁻¹)',
                    yaxis_title='ln(KD)',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02)
                )

                # Run QC evaluation for thermodynamic analysis
                thermo_result_dict = {
                    'deltaH': delta_h,
                    'deltaS': delta_s,
                    'r2': r2,
                    'n_points': len(kd_values),
                    'n_slices': len(temperatures_c),
                    'T_window_start': temperatures_c.min() if len(temperatures_c) > 0 else None,
                    'T_window_end': temperatures_c.max() if len(temperatures_c) > 0 else None,
                    # Would need T_array, F_array, Tm for onset/offset detection
                    # These are not directly available here; could be added if needed
                }

                qc_controller = ThermodynamicQualityController(settings=QCSettings())
                qc_metrics = qc_controller.evaluate(thermo_result_dict)

                # Note: QC results are computed but not currently displayed in Tab 2 UI
                # Could be added to the UI in future enhancement

                return (
                    fig,
                    f"{delta_h_conv:.1f} {delta_h_unit}",
                    f"{delta_s_conv:.1f} {delta_s_unit}",
                    _format_kd(kd_298_raw),
                    _format_kd(kd_310_raw),
                    f"{r2:.4f}"
                )
            else:
                r2_val = result.get('r2') if result else None
                msg = "Van't Hoff fitting failed - insufficient signal variation or poor fit"
                if r2_val is not None and np.isfinite(r2_val):
                    msg += f" (R²={r2_val:.3f})"
                fig.add_annotation(text=msg, xref="paper", yref="paper",
                                   x=0.5, y=0.5, showarrow=False,
                                   font=dict(size=14, color="red"))
                fig.update_layout(template='plotly_white')
                return fig, "Error", "Error", "Error", "--"
                
        except Exception as e:
            fig.add_annotation(
                text=f"Error: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(template='plotly_white')
            return fig, "Error", "Error", "Error", "--", "--"


    @app.callback(
        Output('vh-overlay-plot', 'figure'),
        Input('analysis-results-store', 'data'),
        Input('vh-selection-table', 'selected_rows'),
        State('vh-selection-table', 'data'),
        prevent_initial_call=True
    )
    def update_overlay_plot(results_data, selected_rows, table_data):
        """归一化 AUC 曲线叠加，用于数据质量检查"""
        fig = go.Figure()
        if not results_data or not results_data.get('results'):
            fig.add_annotation(
                text="No data available. Run Basic Analysis first.",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(template='plotly_white')
            return fig
        
        results = results_data['results']

        # 根据选择过滤 - 使用table_data中的idx字段映射到results
        indices = []
        if table_data and selected_rows:
            for table_row_idx in selected_rows:
                if table_row_idx < len(table_data):
                    row = table_data[table_row_idx]
                    original_idx = row.get('idx')  # 获取原始results索引
                    if original_idx is not None and original_idx < len(results):
                        indices.append(original_idx)
        else:
            # 如果没有选择,使用所有数据
            indices = list(range(len(results)))

        # 生成浓度梯度颜色（蓝->红，低到高）
        # 使用更清晰的颜色梯度: 深蓝 -> 青 -> 绿 -> 黄 -> 橙 -> 红
        def _interp_color(val):
            """
            val in [0,1], 使用类似热力图的颜色映射
            0.0: 深蓝 (0, 0, 255)
            0.2: 青色 (0, 255, 255)
            0.4: 绿色 (0, 255, 0)
            0.6: 黄色 (255, 255, 0)
            0.8: 橙色 (255, 128, 0)
            1.0: 红色 (255, 0, 0)
            """
            if val <= 0.2:
                # 深蓝 -> 青
                t = val / 0.2
                r = 0
                g = int(255 * t)
                b = 255
            elif val <= 0.4:
                # 青 -> 绿
                t = (val - 0.2) / 0.2
                r = 0
                g = 255
                b = int(255 * (1 - t))
            elif val <= 0.6:
                # 绿 -> 黄
                t = (val - 0.4) / 0.2
                r = int(255 * t)
                g = 255
                b = 0
            elif val <= 0.8:
                # 黄 -> 橙
                t = (val - 0.6) / 0.2
                r = 255
                g = int(255 * (1 - 0.5 * t))
                b = 0
            else:
                # 橙 -> 红
                t = (val - 0.8) / 0.2
                r = 255
                g = int(128 * (1 - t))
                b = 0

            return f"rgb({r},{g},{b})"

        # 收集浓度并使用对数尺度进行归一化(浓度通常跨越多个数量级)
        concs = []
        for r in results:
            conc_val = r.get('concentration')
            concs.append(conc_val if conc_val is not None else np.nan)
        concs_arr = np.array(concs, dtype=float)

        # 对浓度取对数,以实现视觉上的线性梯度
        valid_concs = concs_arr[np.isfinite(concs_arr) & (concs_arr > 0)]
        if len(valid_concs) > 0:
            log_concs = np.log10(concs_arr, where=(concs_arr > 0), out=np.full_like(concs_arr, np.nan))
            log_min = np.nanmin(log_concs)
            log_max = np.nanmax(log_concs)
            log_span = log_max - log_min if log_max > log_min else 1.0
        else:
            log_concs = concs_arr
            log_min = 0.0
            log_max = 1.0
            log_span = 1.0

        # 准备所有曲线数据并按浓度排序
        traces_data = []
        for i in indices:
            r = results[i]
            conc_val = r.get('concentration')

            # 优先使用进度曲线（基线校正后归一化）以便 AUC 质量检查
            tsb_r2 = r.get('tsb_r2')
            method_used = r.get('method')
            use_progress = r.get('progress_curve') is not None and r.get('progress_temperature') is not None
            low_quality = method_used and 'derivative_fallback' in method_used

            if use_progress and not low_quality:
                T = r.get('progress_temperature')
                F = r.get('progress_curve')
            else:
                T = r.get('T')
                F = r.get('F')
            if not T or not F or len(T) != len(F):
                continue
            F_arr = np.array(F, dtype=float)
            T_arr = np.array(T, dtype=float)
            ptp_val = np.ptp(F_arr)
            if ptp_val == 0:
                continue
            F_norm = (F_arr - F_arr.min()) / ptp_val

            # 颜色按对数浓度梯度映射
            if conc_val is not None and np.isfinite(conc_val) and conc_val > 0:
                log_c = np.log10(conc_val)
                norm_c = np.clip((log_c - log_min) / log_span, 0, 1)
            else:
                norm_c = 0.5
            color = _interp_color(norm_c)

            # 图例文本仅浓度
            legend_name = f"{conc_val:.2E}" if conc_val is not None and np.isfinite(conc_val) else r.get('name', f"sample-{i+1}")

            # 存储曲线数据
            traces_data.append({
                'conc': conc_val if conc_val is not None and np.isfinite(conc_val) else -1,
                'T': T_arr,
                'F': F_norm,
                'color': color,
                'name': legend_name
            })

        # 按浓度从低到高排序(确保图例顺序正确)
        traces_data.sort(key=lambda x: x['conc'])

        # 添加曲线到图中(使用散点模式)
        any_plotted = False
        for trace in traces_data:
            # 使用散点图代替折线图,视觉效果更清晰
            fig.add_trace(go.Scatter(
                x=trace['T'],
                y=trace['F'],
                mode='markers',
                name=trace['name'],
                marker=dict(
                    color=trace['color'],
                    size=2,              # 减小点size,避免遮挡
                    opacity=0.6,         # 降低透明度,减少重叠
                    line=dict(width=0)
                )
            ))
            any_plotted = True
        
        if not any_plotted:
            fig.add_annotation(
                text="No valid curves to display",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
        
        fig.update_layout(
            template='plotly_white',
            title='Normalized curves (0-1)',
            xaxis_title='Temperature (°C)',
            yaxis_title='Normalized Fluorescence',
            legend=dict(
                orientation='v',
                yanchor='top',
                y=1.0,
                x=1.02,
                xanchor='left',
                title=dict(text='Concentration (M)', font=dict(size=12, family='Arial'))
            ),
            margin=dict(l=60, r=20, t=60, b=60)
        )
        return fig


    @app.callback(
        Output('isothermal-ec50-table', 'data'),
        Input('analysis-results-store', 'data'),
        Input('vh-temp-slice-range', 'value'),
        State('slice-step-input', 'value'),
        State('min-dr-input', 'value'),
        State('min-4pl-r2-input', 'value'),
        Input('protein-conc-input', 'value'),
        prevent_initial_call=True
    )
    def build_isothermal_table(results_data, temp_range, slice_step, min_dr, min_r2, protein_conc_input):
        """
        构建等温 EC50/KD 表：
        - 在温度窗口内按 slice_step 生成温度点
        - 对每个温度点：汇总各浓度的插值荧光，归一化，做 4PL 拟合
        - 计算 dynamic range 和 4PL R²，过滤低质量切片
        """
        # 解析蛋白浓度（输入为 M，可带单位）
        protein_conc_m = _parse_protein_conc_to_m(protein_conc_input)

        if not results_data or not results_data.get('results'):
            return []
        results: List[dict] = results_data['results']
        if not temp_range or len(temp_range) != 2:
            return []
        t_min, t_max = temp_range
        if slice_step is None or slice_step <= 0:
            slice_step = 0.5
        temps = np.arange(t_min, t_max + 1e-6, slice_step)
        rows = []

        # 准备浓度与曲线
        concs = []
        curves = []
        for r in results:
            conc = r.get('concentration')
            T = r.get('T')
            F = r.get('F')
            if conc is None or T is None or F is None or len(T) != len(F):
                continue
            concs.append(conc)
            f_arr = np.array(F, dtype=float)
            t_arr = np.array(T, dtype=float)
            f_min = float(f_arr.min())
            f_max = float(f_arr.max())
            curves.append((t_arr, f_arr, f_min, f_max))
        if len(curves) < 3:
            return []

        concs = np.array(concs, dtype=float)

        # 4PL 模型
        def four_pl(x, A, B, C, D):
            return ((A - D) / (1.0 + (x / C) ** B)) + D

        for temp in temps:
            y_values = []
            x_values = []
            for conc, (t_arr, f_arr, f_min, f_max) in zip(concs, curves):
                if temp < t_arr.min() or temp > t_arr.max():
                    continue
                f_interp = np.interp(temp, t_arr, f_arr)
                f_norm = (f_interp - f_min) / (f_max - f_min) if f_max > f_min else 0.0
                y_values.append(f_norm)
                x_values.append(conc)
            if len(y_values) < 3:
                continue
            x = np.array(x_values, dtype=float)
            y = np.array(y_values, dtype=float)
            ptp_raw = np.ptp(y)  # 动态范围基于原始归一化荧光
            if ptp_raw == 0:
                continue
            y_norm = (y - y.min()) / ptp_raw  # 用于 4PL 拟合的0-1归一化
            dr_pct = float(np.clip(ptp_raw, 0, 1) * 100.0)
            if min_dr is not None and dr_pct < min_dr:
                continue
            try:
                from scipy.optimize import curve_fit
                p0 = [1.0, 1.0, np.median(x), 0.0]
                bounds = ([0, 0.01, max(x.min()/10, 1e-12), -0.5], [1.5, 5.0, x.max()*10, 0.5])
                popt, _ = curve_fit(four_pl, x, y_norm, p0=p0, bounds=bounds, maxfev=5000)
                A, B, C, D = popt
                y_fit = four_pl(x, *popt)
                ss_res = np.sum((y_norm - y_fit) ** 2)
                ss_tot = np.sum((y_norm - np.mean(y_norm)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
                if min_r2 is not None and r2 < min_r2:
                    continue
                ec50 = float(C)
                kd = ec50
                if protein_conc_m and protein_conc_m > 0:
                    kd = float(convert_ec50_to_kd(np.array([ec50], dtype=float), protein_conc_m)[0])
                rows.append({
                    "temp": f"{temp:.2f}",
                    "ec50": _format_kd(ec50),
                    "kd": _format_kd(kd),
                    "dr": f"{dr_pct:.1f}%",
                    "r2": f"{r2:.3f}" if np.isfinite(r2) else "N/A",
                    "n_points": len(x)
                })
            except Exception:
                continue
        return rows

