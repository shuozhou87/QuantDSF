#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File Upload Callbacks
======================
文件上传相关回调
"""

from dash import Dash, callback, Input, Output, State, html, ctx, ALL, no_update
import dash_bootstrap_components as dbc
import base64
import io
from pathlib import Path

from app.example_datasets import get_example_dataset, resolve_dataset_files


def register_file_callbacks(app: Dash) -> None:
    """注册文件相关回调"""
    
    @app.callback(
        Output('upload-status', 'children'),
        Output('loaded-files-list', 'children'),
        Output('analysis-results-store', 'data', allow_duplicate=True),
        Input('upload-data', 'contents'),
        Input({'type': 'remove-file-btn', 'index': ALL}, 'n_clicks'),
        State('upload-data', 'filename'),
        prevent_initial_call=True
    )
    def handle_upload_and_remove(contents, remove_clicks, filenames):
        """处理文件上传与删除，避免重复输出冲突"""
        trigger = ctx.triggered_id
        
        # 如果点击了删除按钮，清空状态和结果
        if isinstance(trigger, dict) and trigger.get('type') == 'remove-file-btn':
            if remove_clicks and any(n for n in remove_clicks):
                return "", "", None
            return no_update, no_update, no_update
        
        # 处理上传
        if contents is None:
            return "", "", no_update
        
        if not isinstance(filenames, list):
            filenames = [filenames]
            contents = [contents]
        
        status = dbc.Alert(
            f"✅ {len(filenames)} file(s) uploaded successfully",
            color="success",
            className="py-2"
        )
        
        file_items = []
        for i, name in enumerate(filenames):
            file_items.append(
                dbc.ListGroupItem([
                    html.I(className="fas fa-file-archive me-2 text-primary"),
                    html.Span(name),
                    dbc.Button(
                        html.I(className="fas fa-times"),
                        id={'type': 'remove-file-btn', 'index': i},
                        color="danger",
                        size="sm",
                        outline=True,
                        className="float-end"
                    )
                ], className="d-flex justify-content-between align-items-center py-2")
            )
        
        file_list = dbc.ListGroup(file_items, flush=True)
        
        # 新上传数据时，重置分析结果
        return status, file_list, None

    @app.callback(
        Output('upload-data', 'contents', allow_duplicate=True),
        Output('upload-data', 'filename', allow_duplicate=True),
        Output('method-selector', 'value'),
        Output('channel-selector', 'value'),
        Output('thermodynamic-method-radio', 'value'),
        Output('dual-peak-checkbox', 'value'),
        Input('load-example-data-btn', 'n_clicks'),
        State('example-dataset-selector', 'value'),
        prevent_initial_call=True
    )
    def load_example_data(n_clicks, dataset_id):
        """Load a curated manuscript example dataset."""
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update

        dataset = get_example_dataset(dataset_id)
        if dataset is None:
            print(f"[ERROR] Unknown example dataset: {dataset_id}")
            return no_update, no_update, no_update, no_update, no_update, no_update

        project_root = Path(__file__).resolve().parents[2]
        dataset_paths = list(resolve_dataset_files(dataset, project_root))
        missing = [str(path) for path in dataset_paths if not path.exists()]
        if missing:
            print(f"[ERROR] Example dataset file(s) not found: {missing}")
            return no_update, no_update, no_update, no_update, no_update, no_update
        
        try:
            contents = []
            filenames = []
            for dataset_path in dataset_paths:
                with dataset_path.open('rb') as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                contents.append(f"data:application/zip;base64,{encoded}")
                filenames.append(dataset_path.name)

            print(f"[DEBUG] Loaded example dataset: {dataset.label}")
            return (
                contents,
                filenames,
                dataset.method,
                dataset.channel,
                dataset.thermodynamic_method,
                dataset.dual_peak,
            )
        except Exception as e:
            print(f"[ERROR] Failed to load example dataset: {e}")
            return no_update, no_update, no_update, no_update, no_update, no_update
