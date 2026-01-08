# Desktop Application Feasibility Analysis

**Date**: 2025-12-13
**Status**: Research & Planning
**Goal**: Convert QuantDSF web app to standalone desktop application

## Current Situation

QuantDSF is currently a **Plotly Dash web application** that:
- Runs on Flask development server
- Requires Python environment
- Accessed via browser at http://127.0.0.1:9100
- Must be started from command line with `python app_v2.py`

**Limitations**:
- Users need Python installed
- Must use command line
- Requires browser window
- Cannot be distributed as simple executable

## Research Findings

Based on community research and recent developments (2024-2025), there are **three viable approaches** for creating desktop applications from Dash apps:

### Approach 1: PyWebView + PyInstaller ⭐ RECOMMENDED

**How it works**:
1. Run Dash/Flask server in background thread
2. Use `pywebview` to create native OS window
3. PyWebView loads the Dash app (no browser needed)
4. Bundle everything with PyInstaller into standalone executable

**Advantages**:
- ✅ True native application (no browser required)
- ✅ Small file size compared to Electron
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Active development and good documentation
- ✅ Works well with Dash applications
- ✅ Can use PyInstaller or Nuitka for packaging

**Disadvantages**:
- ❌ Requires code modifications to app startup
- ❌ PyInstaller can be tricky with Dash dependencies
- ❌ May need manual spec file configuration

**Example Implementation**:
```python
import webview
import threading
from app_v2 import app, server

def run_dash():
    """Run Dash server in background thread"""
    app.run_server(debug=False, port=9100, use_reloader=False)

if __name__ == '__main__':
    # Start Dash in background
    t = threading.Thread(target=run_dash)
    t.daemon = True
    t.start()

    # Create native window
    webview.create_window('QuantDSF', 'http://127.0.0.1:9100')
    webview.start()
```

**References**:
- [How to convert a dash app into a standalone Desktop application](https://community.plotly.com/t/how-to-convert-a-dash-app-into-a-standalone-desktop-application/85521)
- [How to build a Python desktop app with pywebview and Flask](https://medium.com/@nohkachi/how-to-build-a-python-desktop-app-with-pywebview-and-flask-73025115e061)
- [pywebview Official Documentation](https://pywebview.flowrl.com/)
- [pywebview GitHub Repository](https://github.com/r0x0r/pywebview)

### Approach 2: Electron + Python Backend

**How it works**:
1. Run Dash server as subprocess
2. Electron creates desktop window
3. Electron loads http://127.0.0.1:9100
4. Package with electron-builder

**Advantages**:
- ✅ Full Electron ecosystem and tooling
- ✅ Rich native features (menus, notifications, etc.)
- ✅ Familiar to JavaScript developers

**Disadvantages**:
- ❌ Large file size (100+ MB due to Chromium)
- ❌ Requires Node.js/JavaScript knowledge
- ❌ More complex build process
- ❌ Need to bundle Python runtime separately
- ❌ More moving parts (Python + Node.js)

**References**:
- [Creating an Electron app with Dash](https://community.plotly.com/t/creating-an-electron-app-with-dash/85430)
- [Wrapping Dash applications for desktop use](https://community.plotly.com/t/wrapping-dash-applications-for-desktop-use/5726)

### Approach 3: PyInstaller Only (No GUI Wrapper)

**How it works**:
1. Package app with PyInstaller
2. User double-clicks .exe
3. Server starts, automatically opens default browser
4. User closes browser tab when done

**Advantages**:
- ✅ Simplest approach
- ✅ No code changes required
- ✅ Small file size

**Disadvantages**:
- ❌ Still requires browser
- ❌ Server keeps running in background
- ❌ Not a "true" desktop app experience
- ❌ User sees command prompt window

**References**:
- [Converting Dash Application to .exe File](https://ploomber.io/blog/dash-exe/)

## Recommended Approach: PyWebView + PyInstaller

### Why This is Best for QuantDSF

1. **True Desktop Experience**: Native window without browser chrome
2. **Reasonable File Size**: 50-100MB vs 150-300MB for Electron
3. **Python-Native**: No need to learn JavaScript/Node.js ecosystem
4. **Cross-Platform**: Works on Windows, macOS, Linux
5. **Active Community**: Good support for Dash applications
6. **Simpler Distribution**: Single executable file

### Implementation Plan

#### Phase 1: Create Desktop Wrapper (1-2 hours)

**Files to create**:

1. **`desktop_app.py`** - Main desktop entry point
```python
"""
QuantDSF Desktop Application
Wraps the Dash web app in a native desktop window using pywebview
"""
import webview
import threading
import sys
import time
from app_v2 import app, server

def run_dash_server():
    """Run Dash server in background thread"""
    try:
        app.run_server(
            debug=False,
            port=9100,
            host='127.0.0.1',
            use_reloader=False
        )
    except Exception as e:
        print(f"Error starting Dash server: {e}")
        sys.exit(1)

def main():
    # Start Dash server in daemon thread
    server_thread = threading.Thread(target=run_dash_server, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(2)

    # Create desktop window
    window = webview.create_window(
        title='QuantDSF - nanoDSF Analysis Platform',
        url='http://127.0.0.1:9100',
        width=1400,
        height=900,
        resizable=True,
        fullscreen=False,
        min_size=(1200, 800)
    )

    # Start GUI loop
    webview.start(debug=False)

if __name__ == '__main__':
    main()
```

2. **Install pywebview**:
```bash
pip install pywebview
```

3. **Test desktop mode**:
```bash
python desktop_app.py
```

#### Phase 2: PyInstaller Configuration (2-3 hours)

**Files to create**:

1. **`quantdsf.spec`** - PyInstaller specification file
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include Dash assets
        ('app', 'app'),
        ('core', 'core'),
    ],
    hiddenimports=[
        'dash',
        'dash_bootstrap_components',
        'plotly',
        'pandas',
        'numpy',
        'scipy',
        'flask',
        'werkzeug',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='QuantDSF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # Optional: add application icon
)
```

2. **Install PyInstaller**:
```bash
pip install pyinstaller
```

3. **Build executable**:
```bash
pyinstaller quantdsf.spec
```

4. **Output**: `dist/QuantDSF.exe` (Windows) or `dist/QuantDSF.app` (macOS)

#### Phase 3: Testing & Refinement (2-3 hours)

**Test cases**:
1. ✅ Application starts without errors
2. ✅ File upload works correctly
3. ✅ All analysis methods produce correct results
4. ✅ Export functionality works
5. ✅ Application closes cleanly
6. ✅ Works on fresh Windows machine without Python

**Common issues to address**:
- Missing dependencies in PyInstaller bundle
- File paths need adjustment (use `sys._MEIPASS` for bundled resources)
- Antivirus false positives (need to sign executable)

### Alternative Tools

If PyInstaller proves difficult, consider:

1. **Nuitka** - Compiles Python to C, faster than PyInstaller
   ```bash
   pip install nuitka
   nuitka --standalone --onefile desktop_app.py
   ```

2. **cx_Freeze** - Another Python freezing tool
   ```bash
   pip install cx_Freeze
   ```

3. **auto-py-to-exe** - GUI wrapper for PyInstaller
   ```bash
   pip install auto-py-to-exe
   auto-py-to-exe
   ```

## File Size Estimates

Based on similar Dash applications:

| Approach | Estimated Size | Components |
|----------|---------------|------------|
| PyWebView + PyInstaller | 50-80 MB | Python runtime, Dash, NumPy, SciPy, pywebview |
| PyWebView + Nuitka | 40-60 MB | Compiled C code, smaller runtime |
| Electron + Python | 150-300 MB | Chromium, Node.js, Python runtime |
| PyInstaller only | 40-70 MB | Python runtime, Dash, NumPy, SciPy (no GUI) |

## Distribution Strategy

### Option 1: GitHub Releases
- Upload `.exe` (Windows) and `.app` (macOS) to GitHub Releases
- Users download and run directly
- Provide checksums for verification

### Option 2: Installer
- Use Inno Setup (Windows) or create `.dmg` (macOS)
- Professional installation experience
- Can add desktop shortcuts, file associations

### Option 3: Internal Network Share
- Place executable on shared drive
- Simple for internal team use
- No external hosting needed

## Security Considerations

1. **Code Signing** (recommended for distribution):
   - Windows: Get code signing certificate
   - macOS: Apple Developer account for notarization
   - Prevents security warnings on user systems

2. **Antivirus False Positives**:
   - PyInstaller executables often flagged
   - Submit to VirusTotal and major AV vendors
   - Code signing helps reduce false positives

3. **User Data Privacy**:
   - All data processed locally (no internet required)
   - No telemetry or data collection
   - Safe for sensitive research data

## Timeline Estimate

| Phase | Time | Complexity |
|-------|------|------------|
| PyWebView integration | 1-2 hours | Low |
| PyInstaller setup | 2-3 hours | Medium |
| Testing & debugging | 2-3 hours | Medium |
| Documentation | 1 hour | Low |
| **Total** | **6-9 hours** | **Medium** |

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| PyInstaller dependency issues | High | Use Nuitka as backup, test thoroughly |
| Large file size | Low | Accept 50-80MB, optimize if needed |
| Platform-specific bugs | Medium | Test on multiple OS versions |
| Antivirus false positives | Medium | Code signing, submit to AV vendors |
| Performance degradation | Low | PyWebView is lightweight, minimal overhead |

## Maintenance Considerations

**Ongoing work required**:
1. Update dependencies regularly for security
2. Rebuild executables when Dash/core libraries update
3. Test on new OS versions (Windows 11, macOS updates)
4. Monitor user reports for platform-specific issues

**Build automation**:
- Can use GitHub Actions to auto-build releases
- Trigger builds on version tags
- Automatically upload to releases page

## Recommendation

**Proceed with PyWebView + PyInstaller approach**:

✅ **Pros**:
- Reasonable development effort (6-9 hours)
- True desktop application experience
- No JavaScript/Node.js learning curve
- Acceptable file size (50-80MB)
- Cross-platform support
- Active community and good documentation

⚠️ **Considerations**:
- Will need PyInstaller spec file tuning
- Should test on multiple Windows versions
- May need code signing for professional distribution

📋 **Next Steps**:
1. Install pywebview: `pip install pywebview`
2. Create `desktop_app.py` wrapper
3. Test desktop mode manually
4. Configure PyInstaller with `quantdsf.spec`
5. Build and test executable
6. Document build process

## Sources

- [How to convert a dash app into a standalone Desktop application - Plotly Community Forum](https://community.plotly.com/t/how-to-convert-a-dash-app-into-a-standalone-desktop-application/85521)
- [Converting a Dash App to a Desktop GUI or Standalone Executable - Plotly Community Forum](https://community.plotly.com/t/converting-a-dash-app-to-a-desktop-gui-or-standalone-executable-are-there-any-guides-available/74381)
- [Creating an Electron app with Dash - Plotly Community Forum](https://community.plotly.com/t/creating-an-electron-app-with-dash/85430)
- [Wrapping Dash applications for desktop use - Plotly Community Forum](https://community.plotly.com/t/wrapping-dash-applications-for-desktop-use/5726)
- [Converting Dash Application to .exe File - Ploomber Blog](https://ploomber.io/blog/dash-exe/)
- [How to build a Python desktop app with pywebview and Flask - Medium](https://medium.com/@nohkachi/how-to-build-a-python-desktop-app-with-pywebview-and-flask-73025115e061)
- [pywebview Official Documentation](https://pywebview.flowrl.com/)
- [pywebview GitHub Repository](https://github.com/r0x0r/pywebview)
