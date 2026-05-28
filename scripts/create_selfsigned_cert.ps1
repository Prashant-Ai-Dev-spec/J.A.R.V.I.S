param(
  [string]$CertPath = "backend\certs",
  [string]$Subject = "CN=jarvis.local"
)

$certDir = Join-Path $PSScriptRoot $CertPath
if (!(Test-Path $certDir)) { New-Item -ItemType Directory -Path $certDir | Out-Null }

$cert = New-SelfSignedCertificate -DnsName "jarvis.local" -CertStoreLocation "Cert:\LocalMachine\My" -NotAfter (Get-Date).AddYears(1)
$pfxPath = Join-Path $certDir "jarvis.pfx"
$password = ConvertTo-SecureString -String "changeit" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $password

# Export PEM files
$certPem = Join-Path $certDir "cert.pem"
$keyPem = Join-Path $certDir "key.pem"
openssl pkcs12 -in $pfxPath -nodes -passin pass:changeit -out $certDir\tmp.pem
Select-String -Path (Join-Path $certDir "tmp.pem") -Pattern "-----BEGIN CERTIFICATE-----" -Context 0,200 | ForEach-Object { $_.Line } > $certPem
Select-String -Path (Join-Path $certDir "tmp.pem") -Pattern "-----BEGIN PRIVATE KEY-----" -Context 0,200 | ForEach-Object { $_.Line } > $keyPem

Write-Output "Created self-signed cert at $certDir"
