#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QuantDSF Desktop Application
==============================
Wraps the Dash web app in a native desktop window using pywebview

Usage:
    python desktop_app.py

Or after PyInstaller packaging:
    QuantDSF.exe (Windows)
    QuantDSF.app (macOS)
"""
import webview
import threading
import time
import sys
import os
from app import create_app


def run_dash_server(port=9100):
    """Run Dash server in background thread"""
    try:
        print(f"[Desktop] Starting Dash server on port {port}...")
        app = create_app(debug=False)
        app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Desktop] Error starting Dash server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for desktop application"""
    # Configuration
    PORT = 9100
    WINDOW_TITLE = 'QuantDSF - nanoDSF Analysis Platform'
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    MIN_WIDTH = 1200
    MIN_HEIGHT = 800

    print("=" * 60)
    print("  QuantDSF Desktop Application")
    print("  Starting...")
    print("=" * 60)

    # Start Dash server in daemon thread
    server_thread = threading.Thread(target=run_dash_server, args=(PORT,), daemon=True)
    server_thread.start()

    # Wait for server to start
    print("[Desktop] Waiting for Dash server to initialize...")
    time.sleep(3)  # Give server time to start

    # Test if server is running
    import urllib.request
    import urllib.error
    max_retries = 10
    for i in range(max_retries):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}', timeout=1)
            print(f"[Desktop] Dash server is ready!")
            break
        except (urllib.error.URLError, OSError):
            if i < max_retries - 1:
                print(f"[Desktop] Server not ready, waiting... ({i+1}/{max_retries})")
                time.sleep(1)
            else:
                print(f"[Desktop] ERROR: Could not connect to Dash server after {max_retries} attempts")
                sys.exit(1)

    # Create desktop window
    print(f"[Desktop] Creating window: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    window = webview.create_window(
        title=WINDOW_TITLE,
        url=f'http://127.0.0.1:{PORT}',
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        resizable=True,
        fullscreen=False,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        background_color='#FFFFFF'
    )

    print("[Desktop] Launching application window...")
    print("=" * 60)

    # Start GUI loop (blocking call)
    webview.start(debug=False)

    print("\n[Desktop] Application closed")


if __name__ == '__main__':
    main()
