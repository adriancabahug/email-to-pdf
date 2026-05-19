# Build script for Email to PDF automation tool
# Usage: .\build.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Email to PDF Build Script ===" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ProjectRoot) {
    $ProjectRoot = Get-Location
}

Set-Location $ProjectRoot

Write-Host "`n[1/6] Installing/updating dependencies..." -ForegroundColor Yellow

python -m pip install --upgrade pip

python -m pip install `
    pywin32>=306 `
    playwright>=1.40.0 `
    requests>=2.31.0 `
    rich>=15.0.0 `
    psutil>=5.9.0 `
    pytest>=8.0.0 `
    pyinstaller>=6.0.0

Write-Host "`n[2/6] Installing Playwright browsers..." -ForegroundColor Yellow
python -m playwright install chromium --with-deps

Write-Host "`n[3/6] Running tests..." -ForegroundColor Yellow
python -m pytest tests/ --ignore=tests/test_playwright_pdf.py -q

if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed. Fix before packaging." -ForegroundColor Red
    exit 1
}

Write-Host "`n[4/6] Cleaning old build artifacts..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "`n[5/6] Building with PyInstaller (onedir)..." -ForegroundColor Yellow

python -m PyInstaller `
    --name "email-to-pdf" `
    --onedir `
    --add-data "src;src" `
    --hidden-import "win32com.client" `
    --hidden-import "win32api" `
    --hidden-import "pythoncom" `
    --hidden-import "playwright" `
    --hidden-import "psutil" `
    --collect-all "playwright" `
    --collect-all "rich" `
    --collect-all "psutil" `
    src/main.py

Write-Host "`n[6/6] Copying Chromium browser to bundle..." -ForegroundColor Yellow
$PlaywrightBrowsersPath = "$env:LOCALAPPDATA\ms-playwright"
$DestBrowsersPath = "dist\email-to-pdf\_internal\playwright-browsers"

if (Test-Path $PlaywrightBrowsersPath) {
    New-Item -ItemType Directory -Path $DestBrowsersPath -Force | Out-Null
    Copy-Item -Path "$PlaywrightBrowsersPath\chromium_headless_shell-1217" -Destination "$DestBrowsersPath\chromium_headless_shell-1217" -Recurse -Force
    Write-Host "  Chromium browser binaries copied." -ForegroundColor Green
} else {
    Write-Host "  [WARN] Playwright browser cache not found at $PlaywrightBrowsersPath" -ForegroundColor Yellow
    Write-Host "  Run: python -m playwright install chromium" -ForegroundColor Yellow
}

Write-Host "`n[6/6] Build complete!" -ForegroundColor Green

$ExePath = "dist/email-to-pdf/email-to-pdf.exe"
if (Test-Path $ExePath) {
    Write-Host "Output: $ExePath" -ForegroundColor Green

    $Size = (Get-Item $ExePath).Length / 1MB
    Write-Host "EXE size: $([math]::Round($Size, 2)) MB" -ForegroundColor Cyan

    $DirSize = (Get-ChildItem "dist/email-to-pdf" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "Total distribution size: $([math]::Round($DirSize, 2)) MB" -ForegroundColor Cyan
} else {
    Write-Host "Build failed - EXE not found" -ForegroundColor Red
    exit 1
}