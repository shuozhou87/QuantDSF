# MinGW64 Installation Guide (Quick Start)

**Required for**: Nuitka desktop app compilation

## Quick Install (5 minutes)

### Step 1: Download MinGW64

**Recommended source**: https://winlibs.com/

**Which file to download?**

Look for the **UCRT runtime** version (recommended for Windows 10/11):

Example filename:
```
winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64ucrt-11.0.1-r5.7z
```

**Key identifiers:**
- `x86_64` - 64-bit (required)
- `posix` - Threading model
- `seh` - Exception handling
- `ucrt` - Universal C Runtime (Windows 10/11)

**Download options:**
- `.7z` format (smaller, requires 7-Zip)
- `.zip` format (larger, works with built-in Windows extraction)

### Step 2: Extract to C:\mingw64

1. **Create destination folder:**
   ```
   C:\mingw64
   ```
   ⚠️ **Important**: No spaces in path!

2. **Extract the downloaded file** to `C:\mingw64`

   After extraction, you should have:
   ```
   C:\mingw64\
   ├── bin\
   │   ├── gcc.exe
   │   ├── g++.exe
   │   └── ...
   ├── include\
   ├── lib\
   └── ...
   ```

3. **Verify** `gcc.exe` exists:
   ```
   dir C:\mingw64\bin\gcc.exe
   ```

### Step 3: Add to PATH Environment Variable

**Option A: Using Command Prompt (User-level)**

```bat
setx PATH "%PATH%;C:\mingw64\bin"
```

**Option B: Using GUI (System-wide, requires admin)**

1. Right-click **This PC** → **Properties**
2. Click **Advanced system settings**
3. Click **Environment Variables**
4. Under **System variables**, select **Path** → **Edit**
5. Click **New**
6. Add: `C:\mingw64\bin`
7. Click **OK** on all dialogs

**Option C: Using PowerShell (User-level)**

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\mingw64\bin", "User")
```

### Step 4: Verify Installation

1. **Close and reopen** Command Prompt (PATH changes don't apply to current session)

2. **Test gcc:**
   ```bat
   gcc --version
   ```

   **Expected output:**
   ```
   gcc (GCC) 13.2.0
   Copyright (C) 2023 Free Software Foundation, Inc.
   This is free software; see the source for copying conditions.
   ```

3. **Test g++:**
   ```bat
   g++ --version
   ```

   Should show similar output.

## Troubleshooting

### "gcc is not recognized as an internal or external command"

**Cause:** MinGW64 not in PATH or PATH not refreshed

**Fix:**
1. Verify file exists: `dir C:\mingw64\bin\gcc.exe`
2. Check PATH: `echo %PATH%` (should contain `C:\mingw64\bin`)
3. **Close and reopen Command Prompt** (critical!)
4. Try again: `gcc --version`

### "The system cannot find the path specified"

**Cause:** Incorrect installation path

**Fix:**
1. Verify extraction: `dir C:\mingw64\bin`
2. Should show `gcc.exe`, `g++.exe`, etc.
3. If not, re-extract to correct location

### PATH not updating

**Cause:** Still using old Command Prompt session

**Fix:**
- **Close all Command Prompt windows**
- **Open new Command Prompt**
- Test again

### Using alternative installation path

If you installed to a different location (e.g., `D:\tools\mingw64`):

1. Use your actual path in the PATH variable
2. Example: `setx PATH "%PATH%;D:\tools\mingw64\bin"`
3. Update `build_nuitka.bat` if it references `C:\mingw64`

## Alternative: Chocolatey Package Manager

If you have Chocolatey installed:

```bat
choco install mingw
```

This automatically:
- Downloads MinGW64
- Installs to `C:\ProgramData\chocolatey\lib\mingw\tools\install\mingw64`
- Adds to PATH

**Verify:**
```bat
gcc --version
```

## After Installation

Once MinGW64 is installed and verified:

1. **Build QuantDSF desktop app:**
   ```bat
   cd C:\Users\rrssd\OneDrive - UT Health San Antonio\QuantDSF\QuantDSF
   build_nuitka.bat
   ```

2. **First build will take 20-40 minutes** (compiling Python to C++)

3. **Result:** `desktop_app.dist\QuantDSF.exe`

## File Sizes

MinGW64 installation:
- Download: ~50-80 MB (compressed)
- Installed: ~300-500 MB (extracted)
- Disk space required: ~600 MB (download + extracted)

## Uninstall

To remove MinGW64:

1. **Remove from PATH:**
   - Open Environment Variables
   - Remove `C:\mingw64\bin` from Path
   - Click OK

2. **Delete folder:**
   ```bat
   rmdir /s /q C:\mingw64
   ```

## References

- **WinLibs (recommended)**: https://winlibs.com/
- **MinGW-w64 official**: https://www.mingw-w64.org/
- **Nuitka documentation**: https://nuitka.net/doc/user-manual.html

## Summary

```
1. Download: winlibs-x86_64-posix-seh-gcc-*-mingw-w64ucrt-*.7z
2. Extract to: C:\mingw64
3. Add to PATH: setx PATH "%PATH%;C:\mingw64\bin"
4. Restart terminal
5. Verify: gcc --version
6. Build: build_nuitka.bat
```

**Total time**: 5-10 minutes (download + setup)
**Next step**: Run `build_nuitka.bat` to create desktop executable
