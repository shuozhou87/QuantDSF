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
        Input('load-test-data-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def load_test_data(n_clicks):
        """加载测试数据集用于调试"""
        if not n_clicks:
            return no_update, no_update
        
        import os
        # 测试数据路径
        test_file_path = "/Users/shuozhou/Library/CloudStorage/OneDrive-UTHealthSanAntonio/QuantDSF/QuantDSF/SampleDataSets/DOSE/RPA+SSDNA_13406_DOSE.zip"
        
        if not os.path.exists(test_file_path):
            print(f"[ERROR] Test file not found: {test_file_path}")
            return no_update, no_update
        
        try:
            with open(test_file_path, 'rb') as f:
                file_content = f.read()
            
            # Encode as base64 for Dash upload component
            encoded = base64.b64encode(file_content).decode('utf-8')
            content_string = f"data:application/zip;base64,{encoded}"
            
            print(f"[DEBUG] Loaded test file: {os.path.basename(test_file_path)}")
            return [content_string], ["RPA+SSDNA_13406_DOSE.zip"]
        except Exception as e:
            print(f"[ERROR] Failed to load test file: {e}")
            return no_update, no_update

