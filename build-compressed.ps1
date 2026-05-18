# Build script for Email to PDF automation tool - optional UPX compressed variant
# Usage: .\build-compressed.ps1
# NOTE: This variant uses UPX compression. This may increase antivirus false positives.
# Use build.ps1 for the stable uncompressed build.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ProjectRoot) {
    $ProjectRoot = Get-Location
}

Set-Location $ProjectRoot

$UpxPath = $null
$UPX_PATHS = @("upx", "C:\Program Files\UPX\upx.exe", "C:\tools\upx.exe")
foreach ($p in $UPX_PATHS) {
    try {
        $null = Get-Command $p -ErrorAction SilentlyContinue
        $UpxPath = $p
        break
    } catch {}
}

if (-not $UpxPath) {
    Write-Host "[WARN] UPX not found in PATH. Install from https://upx.github.io/ or run: choco install upx" -ForegroundColor Yellow
    Write-Host "[WARN] Building without UPX compression..." -ForegroundColor Yellow
}

Write-Host "=== Email to PDF Build Script (UPX variant) ===" -ForegroundColor Cyan

Write-Host "`n[1/6] Cleaning old build artifacts..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "`n[2/6] Building with PyInstaller (onedir)..." -ForegroundColor Yellow

python -m PyInstaller `
    --name "email-to-pdf" `
    --onedir `
    --windowed `
    --add-data "src;src" `
    --hidden-import "win32com.client" `
    --hidden-import "win32api" `
    --hidden-import "pythoncom" `
    --hidden-import "playwright" `
    --hidden-import "psutil" `
    --collect-all "playwright" `
    --collect-all "rich" `
    --collect-all "psutil" `
    src/main_orchestrator.py

$ExePath = "dist/email-to-pdf/email-to-pdf.exe"

if (-not (Test-Path $ExePath)) {
    Write-Host "[FAIL] Build failed - EXE not found" -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/6] Running tests..." -ForegroundColor Yellow
python -m pytest tests/ --ignore=tests/test_playwright_pdf.py -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed. Fix before packaging." -ForegroundColor Red
    exit 1
}

Write-Host "`n[4/6] Measuring baseline size..." -ForegroundColor Yellow
$BaselineSize = (Get-Item $ExePath).Length / 1MB
Write-Host "Baseline EXE size: $([math]::Round($BaselineSize, 2)) MB" -ForegroundColor Cyan

if ($UpxPath) {
    Write-Host "`n[5/6] Applying UPX compression..." -ForegroundColor Yellow
    & $UpxPath --best --force $ExePath 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        $CompressedSize = (Get-Item $ExePath).Length / 1MB
        $Savings = $BaselineSize - $CompressedSize
        Write-Host "Compressed EXE size: $([math]::Round($CompressedSize, 2)) MB" -ForegroundColor Cyan
        Write-Host "Savings: $([math]::Round($Savings, 2)) MB" -ForegroundColor Green
    } else {
        Write-Host "[WARN] UPX compression failed - keeping original EXE" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[5/6] SKIPPED - UPX not available" -ForegroundColor Yellow
}

Write-Host "`n[6/6] Build complete!" -ForegroundColor Green

$FinalSize = (Get-Item $ExePath).Length / 1MB
$DirSize = (Get-ChildItem "dist/email-to-pdf" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host "EXE size: $([math]::Round($FinalSize, 2)) MB" -ForegroundColor Cyan
Write-Host "Total distribution size: $([math]::Round($DirSize, 2)) MB" -ForegroundColor Cyan