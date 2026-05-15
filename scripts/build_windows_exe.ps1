param(
    [ValidateSet("gui", "web", "all")]
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "J.A.R.V.I.S Windows build" -ForegroundColor Cyan

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller
}

if ($Target -in @("gui", "all")) {
    Write-Host "Building GUI EXE..." -ForegroundColor Cyan
    pyinstaller --noconfirm --clean jarvis_gui_build.spec
}

if ($Target -in @("web", "all")) {
    Write-Host "Building Web EXE..." -ForegroundColor Cyan
    pyinstaller --noconfirm --clean jarvis_web.spec
}

Write-Host "Done. Check the dist folder." -ForegroundColor Green
