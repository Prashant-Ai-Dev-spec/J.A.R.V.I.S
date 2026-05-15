param(
    [string]$Token = "",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($Token) {
    $env:JARVIS_WEB_TOKEN = $Token
}

python jarvis_web.py --host 0.0.0.0 --port $Port
