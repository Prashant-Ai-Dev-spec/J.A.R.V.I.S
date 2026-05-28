# Audit rotation script for Windows PowerShell
# Usage: .\scripts\rotate_audit.ps1 -AdminApiKey "KEY" -DaysToKeep 30

param(
    [Parameter(Mandatory=$true)]
    [string]$AdminApiKey,
    
    [Parameter(Mandatory=$false)]
    [int]$DaysToKeep = 30,
    
    [Parameter(Mandatory=$false)]
    [string]$Host = "http://127.0.0.1:8000"
)

Write-Host "[$(Get-Date)] Rotating audit logs - keeping last $DaysToKeep days..." -ForegroundColor Cyan

$response = curl -s -X POST "$Host/admin/audit/rotate" `
  -H "X-Admin-Key: $AdminApiKey" `
  -H "Content-Type: application/json" `
  -d "{`"days`": $DaysToKeep}" | ConvertFrom-Json

Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Green
Write-Host "[$(Get-Date)] Audit rotation complete" -ForegroundColor Green

# Optionally display stats
Write-Host ""
Write-Host "Getting task statistics..." -ForegroundColor Cyan
$stats = curl -s -X GET "$Host/admin/tasks/stats" `
  -H "X-Admin-Key: $AdminApiKey" | ConvertFrom-Json

Write-Host "Total tasks: $($stats.total)" -ForegroundColor Yellow
Write-Host "By Status: $($stats.by_status | ConvertTo-Json)" -ForegroundColor Gray
