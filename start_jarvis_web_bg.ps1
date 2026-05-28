$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = 8765

$Listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Listening) {
    exit 0
}

$env:JARVIS_WEB_TOKEN = "jarvis"
Set-Location $Root

$OutLog = Join-Path $Root "jarvis_web_bg.out.log"
$ErrLog = Join-Path $Root "jarvis_web_bg.err.log"

Start-Process `
    -FilePath "python" `
    -ArgumentList @("jarvis_web.py", "--host", "0.0.0.0", "--port", "$Port") `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog
