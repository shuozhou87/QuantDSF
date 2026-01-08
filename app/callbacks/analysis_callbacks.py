#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis Callbacks
===================
分析相关回调 - 连接 UI 和核心计算层
"""
import base64
import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, callback, Input, Output, State, html, ctx, no_update
import dash_bootstrap_components as dbc
import time
from multiprocessing import Pool, cpu_count
from functools import partial

from core.io.parsers import parse_zip_file
from core.analysis.tm import calc_tm_auc, fit_boltzmann_model
from core.database import HistoryRepository


def _process_single_sample(args):
    """
    Process a single sample - designed for multiprocessing

    Args:
        args: tuple of (cap_data, method, use_tsb_smoothing)

    Returns:
        dict with computed results
    """
    cap, method, use_tsb_smoothing = args

    T = cap['T']
    F = cap['F']

    tm = np.nan
    r2 = 0
    progress_curve = None
    progress_temp = None

    if method == 'auc':
        from core.analysis.tm import calc_tm_auc
        result = calc_tm_auc(T, F, method='progress')
        tm = result.get('Tm_AUC', np.nan)
        r2 = result.get('hill_r2', result.get('quality_score', 0))
        progress_curve = result.get('progress_curve')
        progress_temp = result.get('temperature_range')

    elif method == 'boltzmann':
        from core.analysis.tm import fit_boltzmann_model
        result = fit_boltzmann_model(T, F, model='exponential')
        if result and result.get('success'):
            tm = result['Tm']
            r2 = result['R_squared']
        else:
            tm = np.nan
            r2 = 0
        progress_curve = None
        progress_temp = None

    else:  # derivative
        from core.analysis.tm import compute_derivative, find_derivative_peaks
        T_deriv, deriv = compute_derivative(T, F, use_tsb_smoothing=use_tsb_smoothing or False)
        peaks = find_derivative_peaks(T_deriv, deriv)
        tm = peaks[0][0] if peaks else np.nan

        # Calculate SNR
        if peaks and len(peaks) > 0:
            peak_height = abs(peaks[0][1])
            n_baseline = max(10, int(len(T_deriv) * 0.1))
            baseline_region = deriv[:n_baseline]
            noise_std = np.std(baseline_region)
            r2 = peak_height / noise_std if noise_std > 0 else 0
        else:
            r2 = 0

        progress_curve = deriv.tolist() if isinstance(deriv, np.ndarray) else deriv
        progress_temp = T_deriv.tolist() if isinstance(T_deriv, np.ndarray) else T_deriv

    # Determine quality flag
    if np.isnan(tm):
        quality = "❌"
    elif method == 'derivative':
        quality = "✓" if r2 >= 3.0 else "⚠️"
    elif r2 < 0.9:
        quality = "⚠️"
    else:
        quality = "✓"

    return {
        'name': cap['name'],
        'concentration': cap.get('concentration'),
        'tm': float(tm) if not np.isnan(tm) else None,
        'r_squared': float(r2) if r2 else None,
        'method': method,
        'quality_flag': quality,
        'T': T.tolist() if isinstance(T, np.ndarray) else T,
        'F': F.tolist() if isinstance(F, np.ndarray) else F,
        'progress_curve': progress_curve if progress_curve is not None and not isinstance(progress_curve, np.ndarray) else (progress_curve.tolist() if progress_curve is not None else None),
        'progress_temperature': progress_temp if progress_temp is not None and not isinstance(progress_temp, np.ndarray) else (progress_temp.tolist() if progress_temp is not None else None),
    }


def register_analysis_callbacks(app: Dash) -> None:
    """注册分析相关回调"""

    @app.callback(
        Output('sample-count-badge', 'children'),
        Input('analysis-results-store', 'data'),
    )
    def update_sample_count(results_data):
        """更新样品数量显示"""
        if not results_data or not results_data.get('results'):
            return "0 samples"
        count = len(results_data['results'])
        return f"{count} sample{'s' if count != 1 else ''}"

    @app.callback(
        Output('analysis-results-store', 'data', allow_duplicate=True),
        Output('results-table-container', 'children', allow_duplicate=True),
        Input('results-datatable', 'data'),
        State('analysis-results-store', 'data'),
        prevent_initial_call=True
    )
    def update_concentration_from_table(table_data, results_data):
        """当用户编辑浓度时更新底层数据"""
        if not table_data or not results_data or not results_data.get('results'):
            return no_update, no_update

        results = results_data['results']

        # 解析用户输入的浓度(默认单位为M,不做任何转换)
        for i, row in enumerate(table_data):
            if i >= len(results):
                break

            conc_str = row.get('Concentration (M)', 'N/A')
            if conc_str and conc_str != 'N/A':
                try:
                    # 直接解析为浮点数,默认单位为M
                    conc_val = float(conc_str.strip())
                    results[i]['concentration'] = conc_val
                except (ValueError, AttributeError):
                    # 解析失败,保持原值
                    pass

        # 更新表格以反映新的浓度
        updated_table = _create_results_table(results)

        return {'results': results, 'session_id': results_data.get('session_id')}, updated_table


    @app.callback(
        Output('melting-curves-plot', 'figure', allow_duplicate=True),
        Output('derivative-curves-plot', 'figure'),
        Output('derivative-panel', 'style'),
        Input('results-datatable', 'selected_rows'),
        State('analysis-results-store', 'data'),
        prevent_initial_call=True
    )
    def update_plots_from_selection(selected_rows, results_data):
        """根据表格选择更新图表"""
        if not results_data or not results_data.get('results'):
            return no_update, no_update, no_update

        all_results = results_data['results']

        # 如果没有选中任何行,显示所有数据
        if not selected_rows:
            selected_results = all_results
        else:
            selected_results = [all_results[i] for i in selected_rows]

        # 更新melting curves
        melting_fig = _create_melting_curves_plot(selected_results)

        # 检查是否是derivative方法
        method = all_results[0].get('method', 'auc')
        if method == 'derivative':
            # 创建derivative曲线图
            derivative_fig = _create_derivative_curves_plot(selected_results)
            derivative_style = {'display': 'block'}
        else:
            # 隐藏derivative面板
            derivative_fig = go.Figure()
            derivative_fig.add_annotation(
                text="Select First Derivative method to view derivative curves",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="gray")
            )
            derivative_fig.update_layout(template='plotly_white')
            derivative_style = {'display': 'none'}

        return melting_fig, derivative_fig, derivative_style

    @app.callback(
        Output('analysis-results-store', 'data'),
        Output('results-table-container', 'children'),
        Output('melting-curves-plot', 'figure'),
        Output('tm-distribution-plot', 'figure'),
        Output('derivative-curves-plot', 'figure', allow_duplicate=True),
        Output('derivative-panel', 'style', allow_duplicate=True),
        Input('run-analysis-btn', 'n_clicks'),
        State('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('method-selector', 'value'),
        State('channel-selector', 'value'),
        State('fd-use-tsb-smoothing-checkbox', 'value'),
        State('thermodynamic-method-radio', 'value'),
        State('analysis-results-store', 'data'),
        prevent_initial_call=True
    )
    def run_tm_analysis(n_clicks, contents_list, filenames, method, channel, use_tsb_smoothing, thermodynamic_method, previous_results_data):
        """
        运行 Tm 分析

        1. 解析上传的 ZIP 文件
        2. 对每个毛细管计算 Tm
        3. 生成结果表格和图表
        4. 存储到数据库
        """
        t_start = time.time()
        print(f"\n{'='*60}")
        print(f"PERFORMANCE ANALYSIS - Starting Tm analysis")
        print(f"Method: {method}, Channel: {channel}")
        print(f"{'='*60}")

        if not contents_list:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update
            )
        
        # 确保是列表
        if not isinstance(contents_list, list):
            contents_list = [contents_list]
            filenames = [filenames]
        
        all_capillaries = []
        all_results = []
        
        try:
            # FD方法使用processed数据(Prometheus Panta已平滑)
            # 其他方法使用raw数据
            use_processed = (method == 'derivative')

            # 解析每个上传的文件
            t_parse_start = time.time()
            for content, filename in zip(contents_list, filenames):
                # 解码 base64 内容
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                file_obj = io.BytesIO(decoded)

                # 解析 ZIP 文件
                capillaries = parse_zip_file(
                    file_obj,
                    channel=_map_channel(channel),
                    prefer_processed=use_processed
                )

                # 过滤掉DLS (Dynamic Light Scattering) 相关数据
                # 这些数据不适用于nanoDSF分析
                dls_keywords = ['scattering', 'cumulant radius', 'cumulant_radius']
                filtered_capillaries = []
                for cap in capillaries:
                    sample_name_lower = cap['name'].lower()
                    is_dls = any(keyword.lower() in sample_name_lower for keyword in dls_keywords)
                    if not is_dls:
                        filtered_capillaries.append(cap)

                all_capillaries.extend(filtered_capillaries)

            t_parse_end = time.time()
            print(f"[TIMING] File parsing: {t_parse_end - t_parse_start:.3f}s for {len(all_capillaries)} samples")

            if not all_capillaries:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update
                )
            
            # 对每个毛细管计算 Tm
            t_compute_start = time.time()

            # Determine number of CPU cores to use
            n_cores = max(1, cpu_count() - 1)  # Leave one core for system
            use_parallel = len(all_capillaries) >= 10  # Only use parallel for 10+ samples

            if use_parallel:
                print(f"[PARALLEL] Using {n_cores} CPU cores for {len(all_capillaries)} samples")

                # Prepare arguments for parallel processing
                args_list = [(cap, method, use_tsb_smoothing) for cap in all_capillaries]

                # Process in parallel
                with Pool(processes=n_cores) as pool:
                    all_results = pool.map(_process_single_sample, args_list)

                computation_times = []  # Not tracking individual times in parallel mode
                print(f"[PARALLEL] Parallel computation completed")
            else:
                print(f"[SERIAL] Using single-threaded processing for {len(all_capillaries)} samples")
                all_results = []
                computation_times = []

                for i, cap in enumerate(all_capillaries):
                    t_sample_start = time.time()
                    result_dict = _process_single_sample((cap, method, use_tsb_smoothing))
                    all_results.append(result_dict)

                    t_sample_end = time.time()
                    sample_time = t_sample_end - t_sample_start
                    computation_times.append(sample_time)
                    if i < 5 or i % 10 == 0:
                        print(f"[TIMING] Sample {i+1}/{len(all_capillaries)} ({cap['name']}): {sample_time:.3f}s")

            # Now process thermodynamic analysis for each result (must be serial due to dependencies)
            for i, result_dict in enumerate(all_results):
                cap = all_capillaries[i]
                T = cap['T']
                F = cap['F']
                tm = result_dict['tm']
                progress_curve = result_dict['progress_curve']
                progress_temp = result_dict['progress_temperature']

                # Single-Curve Thermodynamic Analysis (Wright 2017)
                if thermodynamic_method == 'single_curve' and not np.isnan(tm):
                    try:
                        from core.analysis.thermodynamics.single_curve import extract_thermodynamics_single_curve

                        # 准备baseline数据（如果有的话，来自AUC Progress分析）
                        baseline_fold = None
                        baseline_unfold = None

                        # 尝试从AUC analysis获取baseline
                        if method in ('auc', 'boltzmann'):
                            # 这些方法可能包含baseline信息
                            # 暂时使用progress_curve（已归一化的P_f）
                            pass

                        # 运行Single-Curve分析
                        thermo_result = extract_thermodynamics_single_curve(
                            T=T,
                            F=F,
                            Tm=tm,
                            progress_curve=np.array(progress_curve) if progress_curve else None,
                            baseline_fold=baseline_fold,
                            baseline_unfold=baseline_unfold
                        )

                        if thermo_result['success']:
                            result_dict['delta_G_std'] = thermo_result['delta_G_std']
                            result_dict['delta_H_std'] = thermo_result['delta_H_std']
                            result_dict['delta_S_std'] = thermo_result['delta_S_std']
                            result_dict['thermo_r2'] = thermo_result['R_squared']
                            result_dict['thermo_valid'] = thermo_result['valid']
                            result_dict['thermo_warnings'] = '; '.join(thermo_result.get('warnings', []))
                        else:
                            result_dict['delta_G_std'] = None
                            result_dict['delta_H_std'] = None
                            result_dict['delta_S_std'] = None
                            result_dict['thermo_r2'] = None
                            result_dict['thermo_valid'] = False
                            result_dict['thermo_warnings'] = thermo_result.get('error', 'Analysis failed')
                    except Exception as e:
                        # Thermodynamic analysis失败不影响Tm结果
                        result_dict['delta_G_std'] = None
                        result_dict['delta_H_std'] = None
                        result_dict['delta_S_std'] = None
                        result_dict['thermo_r2'] = None
                        result_dict['thermo_valid'] = False
                        result_dict['thermo_warnings'] = f'Error: {str(e)}'

                # Note: result_dict is already in all_results (from parallel or serial processing)
                # Thermodynamic data was added in-place to existing result_dict

            # 保留用户手动编辑的浓度信息
            # 只有在数据集未变化的情况下才保留浓度(通过比较文件名判断)
            if previous_results_data and 'results' in previous_results_data and 'filenames' in previous_results_data:
                # 检查是否是同一个数据集(文件名相同)
                prev_filenames = previous_results_data.get('filenames', [])
                same_dataset = (prev_filenames == filenames)

                if same_dataset:
                    previous_results = previous_results_data['results']
                    # 创建样品名到浓度的映射
                    prev_conc_map = {r['name']: r.get('concentration') for r in previous_results}

                    # 更新新结果中的浓度(如果之前有手动输入过)
                    for result in all_results:
                        sample_name = result['name']
                        if sample_name in prev_conc_map:
                            prev_conc = prev_conc_map[sample_name]
                            # 只有当之前的浓度不为None时才覆盖(保留用户输入)
                            if prev_conc is not None:
                                result['concentration'] = prev_conc

            t_compute_end = time.time()
            total_compute_time = t_compute_end - t_compute_start
            avg_time = total_compute_time / len(all_results) if all_results else 0
            print(f"\n[TIMING] Total computation: {total_compute_time:.3f}s for {len(all_results)} samples")
            print(f"[TIMING] Average per sample: {avg_time:.3f}s")
            if computation_times:
                print(f"[TIMING] Min: {np.min(computation_times):.3f}s, Max: {np.max(computation_times):.3f}s")
            if use_parallel:
                speedup = 163.964 / total_compute_time if total_compute_time > 0 else 0  # Compare to serial baseline
                print(f"[PARALLEL] Speedup: {speedup:.2f}x (estimated vs serial)")

            # 保存到数据库
            t_db_start = time.time()
            repo = HistoryRepository()
            session_id = repo.save_complete_analysis(
                name=f"Analysis - {filenames[0] if filenames else 'Unknown'}",
                source_files=filenames,
                tm_results=all_results,
                channel=channel,
                method=method
            )
            t_db_end = time.time()
            print(f"[TIMING] Database save: {t_db_end - t_db_start:.3f}s")

            # 生成结果表格
            t_table_start = time.time()
            table = _create_results_table(all_results)
            t_table_end = time.time()
            print(f"[TIMING] Table creation: {t_table_end - t_table_start:.3f}s")

            # 生成图表
            t_plot_start = time.time()
            curves_fig = _create_melting_curves_plot(all_results)
            dist_fig = _create_tm_distribution_plot(all_results)
            t_plot_end = time.time()
            print(f"[TIMING] Plot creation: {t_plot_end - t_plot_start:.3f}s")
            
            status = dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Analysis complete! Processed {len(all_results)} samples. Results saved (Session #{session_id})"
            ], color="success", className="mt-2")

            # 创建derivative图表(如果是derivative方法)
            if method == 'derivative':
                derivative_fig = _create_derivative_curves_plot(all_results)
                derivative_style = {'display': 'block'}
            else:
                derivative_fig = go.Figure()
                derivative_fig.add_annotation(
                    text="Select First Derivative method to view derivative curves",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color="gray")
                )
                derivative_fig.update_layout(template='plotly_white')
                derivative_style = {'display': 'none'}

            t_end = time.time()
            total_time = t_end - t_start
            print(f"\n[TIMING] TOTAL ANALYSIS TIME: {total_time:.3f}s")
            print(f"{'='*60}\n")

            return (
                {'results': all_results, 'session_id': session_id, 'filenames': filenames},
                table,
                curves_fig,
                dist_fig,
                derivative_fig,
                derivative_style
            )

        except Exception as e:
            import traceback
            print(f"ERROR in run_tm_analysis: {e}")
            print(traceback.format_exc())
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update
            )


def _map_channel(channel: str) -> str:
    """映射通道名称"""
    mapping = {
        'ratio': '350/330 nm ratio',
        '350': '350 nm',
        '330': '330 nm'
    }
    return mapping.get(channel, channel)


def _create_results_table(results: list):
    """创建结果表格 - 使用DataTable支持复选框"""
    from dash import dash_table
    from core.utils import format_concentration

    # Detect method to determine column header
    method = results[0]['method'] if results else 'auc'
    is_derivative = method == 'derivative'
    quality_col_header = "SNR" if is_derivative else "R²"

    # Check if thermodynamic data is available
    has_thermo_data = any(r.get('delta_G_std') is not None for r in results)

    # 准备数据
    table_data = []
    for i, r in enumerate(results):
        conc_str = format_concentration(r['concentration']) if r['concentration'] else 'N/A'
        tm_str = f"{r['tm']:.1f}" if r['tm'] is not None else 'N/A'

        # Format SNR with 1 decimal, R² with 3 decimals
        if r['method'] == 'derivative':
            r2_str = f"{r['r_squared']:.1f}" if r['r_squared'] is not None else 'N/A'
        else:
            r2_str = f"{r['r_squared']:.3f}" if r['r_squared'] is not None else 'N/A'

        row_data = {
            'index': i,
            'Sample': r['name'],
            'Concentration (M)': conc_str,
            'Tm (°C)': tm_str,
            quality_col_header: r2_str,
            'Method': r['method'].upper(),
            'Status': r['quality_flag']
        }

        # Add thermodynamic parameters if available
        if has_thermo_data:
            row_data['ΔG° (kJ/mol)'] = f"{r['delta_G_std']:.1f}" if r.get('delta_G_std') is not None else 'N/A'
            row_data['ΔH° (kJ/mol)'] = f"{r['delta_H_std']:.0f}" if r.get('delta_H_std') is not None else 'N/A'
            row_data['ΔS° (J/mol·K)'] = f"{r['delta_S_std']*1000:.1f}" if r.get('delta_S_std') is not None else 'N/A'  # Convert kJ to J for display
            row_data['Thermo R²'] = f"{r['thermo_r2']:.3f}" if r.get('thermo_r2') is not None else 'N/A'
            row_data['Thermo'] = "✓" if r.get('thermo_valid') else ("⚠️" if r.get('delta_G_std') is not None else "--")

        table_data.append(row_data)

    # 定义列 - Concentration (M)列设为可编辑
    columns = [
        {"name": "Sample", "id": "Sample", "editable": False},
        {"name": "Concentration (M)", "id": "Concentration (M)", "editable": True},
        {"name": "Tm (°C)", "id": "Tm (°C)", "editable": False},
        {"name": quality_col_header, "id": quality_col_header, "editable": False},
        {"name": "Method", "id": "Method", "editable": False},
        {"name": "Status", "id": "Status", "editable": False}
    ]

    # Add thermodynamic columns if data is available
    if has_thermo_data:
        columns.extend([
            {"name": "ΔG° (kJ/mol)", "id": "ΔG° (kJ/mol)", "editable": False},
            {"name": "ΔH° (kJ/mol)", "id": "ΔH° (kJ/mol)", "editable": False},
            {"name": "ΔS° (J/mol·K)", "id": "ΔS° (J/mol·K)", "editable": False},
            {"name": "Thermo R²", "id": "Thermo R²", "editable": False},
            {"name": "Thermo", "id": "Thermo", "editable": False}
        ])

    return dash_table.DataTable(
        id='results-datatable',
        columns=columns,
        data=table_data,
        editable=True,  # 启用编辑
        row_selectable='multi',
        selected_rows=list(range(len(results))),  # 默认全选
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontFamily': 'Arial, sans-serif'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'borderBottom': '2px solid #dee2e6'
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'Concentration (M)'},
                'backgroundColor': '#fff9e6',  # 浅黄色背景表示可编辑
            },
            {
                'if': {'column_id': 'Status', 'filter_query': '{Status} = "✓"'},
                'backgroundColor': '#d4edda',
                'color': '#155724'
            },
            {
                'if': {'column_id': 'Status', 'filter_query': '{Status} = "⚠️"'},
                'backgroundColor': '#fff3cd',
                'color': '#856404'
            },
            {
                'if': {'column_id': 'Status', 'filter_query': '{Status} = "❌"'},
                'backgroundColor': '#f8d7da',
                'color': '#721c24'
            },
            {
                'if': {'column_id': 'Thermo', 'filter_query': '{Thermo} = "✓"'},
                'backgroundColor': '#d4edda',
                'color': '#155724'
            },
            {
                'if': {'column_id': 'Thermo', 'filter_query': '{Thermo} = "⚠️"'},
                'backgroundColor': '#fff3cd',
                'color': '#856404'
            },
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        style_as_list_view=True,
    )


def _create_melting_curves_plot(results: list) -> go.Figure:
    """创建熔解曲线图 - 使用蓝到红渐变散点图"""
    fig = go.Figure()

    # 浓度梯度颜色映射函数（蓝->红）
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

    # 收集浓度并使用对数尺度进行归一化
    concs = []
    for r in results:
        conc_val = r.get('concentration')
        concs.append(conc_val if conc_val is not None else np.nan)
    concs_arr = np.array(concs, dtype=float)

    # 检测是否有有效的浓度信息
    valid_concs = concs_arr[np.isfinite(concs_arr) & (concs_arr > 0)]
    has_concentration_data = len(valid_concs) > 0

    # 准备所有曲线数据
    traces_data = []

    if has_concentration_data:
        # 有浓度数据：使用浓度梯度颜色映射
        log_concs = np.log10(concs_arr, where=(concs_arr > 0), out=np.full_like(concs_arr, np.nan))
        log_min = np.nanmin(log_concs)
        log_max = np.nanmax(log_concs)
        log_span = log_max - log_min if log_max > log_min else 1.0

        for i, r in enumerate(results):
            if r.get('T') and r.get('F'):
                conc_val = r.get('concentration')
                T = r['T']
                F = r['F']

                # 颜色按对数浓度梯度映射
                if conc_val is not None and np.isfinite(conc_val) and conc_val > 0:
                    log_c = np.log10(conc_val)
                    norm_c = np.clip((log_c - log_min) / log_span, 0, 1)
                    color = _interp_color(norm_c)
                    legend_name = f"{conc_val:.2E} M"
                else:
                    # 有浓度数据但当前样品无浓度：使用灰色
                    norm_c = 0.5
                    color = 'rgb(128,128,128)'
                    legend_name = r.get('name', f"sample-{i+1}")

                traces_data.append({
                    'conc': conc_val if conc_val is not None and np.isfinite(conc_val) else -1,
                    'T': T,
                    'F': F,
                    'color': color,
                    'name': legend_name
                })

        # 按浓度从低到高排序(确保图例顺序正确)
        traces_data.sort(key=lambda x: x['conc'])
        legend_title = 'Concentration'

    else:
        # 无浓度数据：每个样品使用不同颜色
        n_samples = len(results)
        for i, r in enumerate(results):
            if r.get('T') and r.get('F'):
                T = r['T']
                F = r['F']

                # 为每个样品分配不同的颜色(均匀分布在0-1范围内)
                norm_c = i / max(n_samples - 1, 1)
                color = _interp_color(norm_c)
                legend_name = r.get('name', f"sample-{i+1}")

                traces_data.append({
                    'index': i,
                    'T': T,
                    'F': F,
                    'color': color,
                    'name': legend_name
                })

        legend_title = 'Samples'

    # 添加曲线到图中(使用散点模式)
    for trace in traces_data:
        fig.add_trace(go.Scatter(
            x=trace['T'],
            y=trace['F'],
            mode='markers',
            name=trace['name'],
            marker=dict(
                color=trace['color'],
                size=2,              # 小点size
                opacity=0.6,         # 降低透明度
                line=dict(width=0)
            )
        ))

    fig.update_layout(
        template='plotly_white',
        title='Melting Curves',
        xaxis_title='Temperature (°C)',
        yaxis_title='Fluorescence',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1.0,
            x=1.02,
            xanchor='left',
            title=dict(text=legend_title, font=dict(size=12, family='Arial'))
        ),
        margin=dict(l=60, r=20, t=60, b=60)
    )

    return fig


def _create_derivative_curves_plot(results: list) -> go.Figure:
    """创建First Derivative曲线图"""
    fig = go.Figure()

    # 使用与melting curves相同的颜色映射
    def _interp_color(val):
        """颜色映射函数(蓝->红)"""
        if val <= 0.2:
            t = val / 0.2
            r, g, b = 0, int(255 * t), 255
        elif val <= 0.4:
            t = (val - 0.2) / 0.2
            r, g, b = 0, 255, int(255 * (1 - t))
        elif val <= 0.6:
            t = (val - 0.4) / 0.2
            r, g, b = int(255 * t), 255, 0
        elif val <= 0.8:
            t = (val - 0.6) / 0.2
            r, g, b = 255, int(255 * (1 - 0.5 * t)), 0
        else:
            t = (val - 0.8) / 0.2
            r, g, b = 255, int(128 * (1 - t)), 0
        return f"rgb({r},{g},{b})"

    # 收集浓度并归一化
    concs = []
    for r in results:
        conc_val = r.get('concentration')
        concs.append(conc_val if conc_val is not None else np.nan)
    concs_arr = np.array(concs, dtype=float)

    # 检测是否有有效的浓度信息
    valid_concs = concs_arr[np.isfinite(concs_arr) & (concs_arr > 0)]
    has_concentration_data = len(valid_concs) > 0

    # 准备曲线数据
    traces_data = []

    if has_concentration_data:
        # 有浓度数据：使用浓度梯度颜色映射
        log_concs = np.log10(concs_arr, where=(concs_arr > 0), out=np.full_like(concs_arr, np.nan))
        log_min = np.nanmin(log_concs)
        log_max = np.nanmax(log_concs)
        log_span = log_max - log_min if log_max > log_min else 1.0

        for i, r in enumerate(results):
            if r.get('progress_temperature') and r.get('progress_curve'):
                conc_val = r.get('concentration')
                T_deriv = r['progress_temperature']
                deriv = r['progress_curve']

                # 颜色映射
                if conc_val is not None and np.isfinite(conc_val) and conc_val > 0:
                    log_c = np.log10(conc_val)
                    norm_c = np.clip((log_c - log_min) / log_span, 0, 1)
                    color = _interp_color(norm_c)
                    legend_name = f"{conc_val:.2E} M"
                else:
                    # 有浓度数据但当前样品无浓度：使用灰色
                    color = 'rgb(128,128,128)'
                    legend_name = r.get('name', f"sample-{i+1}")

                traces_data.append({
                    'conc': conc_val if conc_val is not None and np.isfinite(conc_val) else -1,
                    'T': T_deriv,
                    'deriv': deriv,
                    'color': color,
                    'name': legend_name
                })

        # 按浓度排序
        traces_data.sort(key=lambda x: x['conc'])
        legend_title = 'Concentration'

    else:
        # 无浓度数据：每个样品使用不同颜色
        n_samples = sum(1 for r in results if r.get('progress_temperature') and r.get('progress_curve'))
        sample_idx = 0

        for i, r in enumerate(results):
            if r.get('progress_temperature') and r.get('progress_curve'):
                T_deriv = r['progress_temperature']
                deriv = r['progress_curve']

                # 为每个样品分配不同的颜色
                norm_c = sample_idx / max(n_samples - 1, 1)
                color = _interp_color(norm_c)
                legend_name = r.get('name', f"sample-{i+1}")

                traces_data.append({
                    'index': sample_idx,
                    'T': T_deriv,
                    'deriv': deriv,
                    'color': color,
                    'name': legend_name
                })

                sample_idx += 1

        legend_title = 'Samples'

    # 添加曲线
    for trace in traces_data:
        fig.add_trace(go.Scatter(
            x=trace['T'],
            y=trace['deriv'],
            mode='lines',
            name=trace['name'],
            line=dict(color=trace['color'], width=1.5),
            opacity=0.8
        ))

    fig.update_layout(
        template='plotly_white',
        title='First Derivative Curves (dF/dT)',
        xaxis_title='Temperature (°C)',
        yaxis_title='dF/dT',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1.0,
            x=1.02,
            xanchor='left',
            title=dict(text=legend_title, font=dict(size=12, family='Arial'))
        ),
        margin=dict(l=60, r=20, t=60, b=60)
    )

    # 添加零线
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1, opacity=0.5)

    return fig


def _create_tm_distribution_plot(results: list) -> go.Figure:
    """创建 Tm 分布图"""
    fig = go.Figure()
    
    # 过滤有效结果
    valid_results = [r for r in results if r['tm'] is not None]
    
    if not valid_results:
        fig.add_annotation(
            text="No valid Tm values",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
    else:
        names = [r['name'] for r in valid_results]
        tms = [r['tm'] for r in valid_results]
        colors = ['#3498db' if r['quality_flag'] == '✓' else '#e74c3c' for r in valid_results]
        
        fig.add_trace(go.Bar(
            x=names,
            y=tms,
            marker_color=colors
        ))
        
        # 添加平均线
        mean_tm = np.mean(tms)
        fig.add_hline(y=mean_tm, line_dash="dash", line_color="gray",
                     annotation_text=f"Mean: {mean_tm:.1f}°C")
    
    fig.update_layout(
        template='plotly_white',
        title='Tm Distribution',
        xaxis_title='Sample',
        yaxis_title='Tm (°C)',
        margin=dict(l=60, r=20, t=60, b=100),
        xaxis_tickangle=-45
    )
    
    return fig

