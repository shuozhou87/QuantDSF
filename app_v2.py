#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QuantDSF v2 - Application Entry Point
======================================
启动 Dash 应用

使用方法:
    python app_v2.py
    
    或指定端口:
    python app_v2.py --port 8051
"""

import argparse
from app import create_app


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description='QuantDSF v2 - nanoDSF Analysis Platform')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to')
    args = parser.parse_args()
    
    print("=" * 60)
    print("  QuantDSF v2 - nanoDSF Analysis Platform")
    print(f"  Open http://{args.host}:{args.port} in your browser")
    print("=" * 60)
    
    app = create_app(debug=args.debug)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()


