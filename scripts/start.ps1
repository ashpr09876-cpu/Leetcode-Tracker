<#
  Start CodeTrack.
    scripts\start.ps1          Development mode: Docker runs PostgreSQL+Redis; backend and frontend run in two new windows.
                               Open http://localhost:5173
    scripts\start.ps1 -Docker  Everything in Docker (builds images the first time). Open http://localhost:8080
#>
param([switch]$Docker)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path ".env")) { Write-Host "Run scripts\setup.ps1 first." -ForegroundColor Red; exit 1 }
docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "Docker is not running. Start Docker Desktop and try again." -ForegroundColor Red; exit 1 }

if ($Docker) {
  docker compose --profile full up -d --build
  if ($LASTEXITCODE -ne 0) { Write-Host "docker compose failed - see the message above." -ForegroundColor Red; exit 1 }
  Write-Host "`nCodeTrack is starting. Open http://localhost:8080 (give the backend ~20 seconds on first run)." -ForegroundColor Green
  Write-Host "Password-reset links appear in:  docker compose logs backend"
  exit 0
}

docker compose up -d db redis
if ($LASTEXITCODE -ne 0) { Write-Host "Could not start the database containers." -ForegroundColor Red; exit 1 }
Write-Host "Waiting for PostgreSQL..."
for ($i = 0; $i -lt 30; $i++) {
  $h = docker inspect -f "{{.State.Health.Status}}" (docker compose ps -q db) 2>$null
  if ($h -eq "healthy") { break }; Start-Sleep -Seconds 2
}
if ($h -ne "healthy") { Write-Host "PostgreSQL did not become healthy. Check: docker compose logs db" -ForegroundColor Red; exit 1 }

Push-Location backend
& ".venv\Scripts\python.exe" -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "Database migration failed - see the error above." -ForegroundColor Red; exit 1 }
Pop-Location

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
Write-Host "`nStarted. Open http://localhost:5173 in your browser." -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/api/docs   |   Password-reset links print in the backend window."
