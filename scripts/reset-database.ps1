<# Deletes ALL CodeTrack data in the local database and recreates the tables. Asks for confirmation. #>
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$a = Read-Host "This permanently deletes every account and problem in your LOCAL database. Type RESET to continue"
if ($a -ne "RESET") { Write-Host "Cancelled."; exit 0 }
docker compose --profile full down -v
docker compose up -d db redis
Write-Host "Waiting for PostgreSQL..."
for ($i = 0; $i -lt 30; $i++) { $h = docker inspect -f "{{.State.Health.Status}}" (docker compose ps -q db) 2>$null; if ($h -eq "healthy") { break }; Start-Sleep -Seconds 2 }
Push-Location backend
& ".venv\Scripts\python.exe" -m alembic upgrade head
Pop-Location
Write-Host "Database reset. Start the app again with scripts\start.ps1" -ForegroundColor Green
