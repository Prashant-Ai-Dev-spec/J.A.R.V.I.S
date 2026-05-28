param(
  [string]$ComposeFile = "docker-compose.yml"
)

Write-Output "Bringing up services via docker-compose"
docker-compose -f $ComposeFile up --build -d
