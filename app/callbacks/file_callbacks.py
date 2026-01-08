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

