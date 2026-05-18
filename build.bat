@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo  Building Email to PDF EXE
echo ============================================
echo.

:: --- CONFIG -----------------------------------------------------------
set "ENTRY_POINT=src\main.py"
set "EXE_NAME=email-to-pdf"

:: --- [1/5] Dependencies ------------------------------------------------
echo [1/5] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

:: --- [2/5] PyInstaller -------------------------------------------------
echo.
echo [2/5] Installing PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)

:: --- [3/5] Playwright browsers -----------------------------------------
echo.
echo [3/5] Ensuring Playwright browsers are installed...
playwright install chromium
if %errorlevel% neq 0 (
    echo WARNING: Playwright browser install failed. The EXE may need manual browser setup.
)

:: --- Discover actual Playwright browser paths ---------------------------
set "PLAYWRIGHT_DIR=%LOCALAPPDATA%\ms-playwright"
set "BROWSER_ARGS="

if exist "%PLAYWRIGHT_DIR%" (
    for /d %%D in ("%PLAYWRIGHT_DIR%\chromium*") do (
        set "BROWSER_ARGS=!BROWSER_ARGS! --add-data "%%D;playwright-browsers/%%~nD""
    )
    for /d %%D in ("%PLAYWRIGHT_DIR%\ffmpeg*") do (
        set "BROWSER_ARGS=!BROWSER_ARGS! --add-data "%%D;playwright-browsers/%%~nD""
    )
) else (
    echo WARNING: Playwright browser directory not found. EXE may fail at runtime.
)

:: --- [4/5] Pre-build import check --------------------------------------
echo.
echo [4/5] Checking for stale imports to deleted modules...
python -c "import src.main_orchestrator, src.email_searcher, src.email_formatter, src.license_validator, src.cli"
if %errorlevel% neq 0 (
    echo ERROR: Stale imports found. Remove references to deleted modules:
    echo   - outlook_connection, stdin_guard, execution_mode, input_handler, contact_registry
    pause
    exit /b 1
)

:: --- [5/5] Build -------------------------------------------------------
echo.
echo [5/5] Building EXE with PyInstaller...
echo Entry point: %ENTRY_POINT%
echo.

pyinstaller --onefile ^
    --name %EXE_NAME% ^
    --hidden-import win32com ^
    --hidden-import win32com.client ^
    --hidden-import pythoncom ^
    --hidden-import pywintypes ^
    --hidden-import win32timezone ^
    --hidden-import playwright ^
    --hidden-import rich ^
    --hidden-import rich.prompt ^
    %BROWSER_ARGS% ^
    %ENTRY_POINT%

if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete!
echo  EXE location: dist\%EXE_NAME%.exe
echo ============================================
echo.
echo IMPORTANT: Before distributing:
echo 1. Verify LICENSE_SERVER_URL in src\dependencies.py (CompositionRoot)
echo 2. Test the EXE on a clean machine with Outlook installed
echo 3. Ensure the target machine has the same Windows/Outlook bitness
echo.
pause