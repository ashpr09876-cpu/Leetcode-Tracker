# Stops Docker services. Close the backend/frontend PowerShell windows (Ctrl+C) yourself in development mode.
# Add -RemoveData to also delete the database volume.
param([switch]$RemoveData)
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($RemoveData) { docker compose --profile full down -v } else { docker compose --profile full down }
Write-Host "Docker services stopped." -ForegroundColor Green
