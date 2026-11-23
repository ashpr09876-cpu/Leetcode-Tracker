<#
  CodeTrack setup. Run from the project root:   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
  Checks prerequisites, creates .env files with RANDOM secrets, installs dependencies.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Test-Tool($name, $cmd, $hint) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { Write-Host "[ok] $name found" -ForegroundColor Green; return $true }
  Write-Host "[missing] $name - $hint" -ForegroundColor Yellow; return $false
}
function New-Secret([int]$bytes = 32) {
  $b = New-Object byte[] $bytes
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  return ([Convert]::ToBase64String($b) -replace '[+/=]', 'x')
}

Write-Host "`n== Prerequisites ==" -ForegroundColor Cyan
$docker = Test-Tool "Docker" "docker" "install Docker Desktop: https://www.docker.com/products/docker-desktop/ (then start it)"
$node   = Test-Tool "Node.js 20+" "node" "install the LTS version from https://nodejs.org"
$py     = Test-Tool "Python 3.12" "python" "install from https://www.python.org/downloads/ (tick 'Add python.exe to PATH')"
if (-not ($docker -and $node -and $py)) { Write-Host "`nInstall the missing tools, open a NEW PowerShell window, and run this script again." -ForegroundColor Red; exit 1 }
docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "[problem] Docker is installed but not running. Start Docker Desktop, wait for the whale icon to say 'running', then retry." -ForegroundColor Red; exit 1 }
$pyv = (python --version) 2>&1
Write-Host "Python: $pyv"
if ($pyv -notmatch "3\.(1[2-9]|[2-9]\d)") { Write-Host "[warning] Python 3.12+ is recommended." -ForegroundColor Yellow }

Write-Host "`n== Environment files ==" -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
  $pg = New-Secret 18; $sk = New-Secret 48
  (Get-Content ".env.example") -replace 'POSTGRES_PASSWORD=CHANGE_ME', "POSTGRES_PASSWORD=$pg" -replace 'SECRET_KEY=CHANGE_ME_TO_A_LONG_RANDOM_STRING', "SECRET_KEY=$sk" | Set-Content ".env" -Encoding UTF8
  (Get-Content "backend\.env.example") -replace 'CHANGE_ME_TO_A_LONG_RANDOM_STRING', $sk -replace 'codetrack:CHANGE_ME@', "codetrack:$pg@" | Set-Content "backend\.env" -Encoding UTF8
  Write-Host "Created .env and backend\.env with random secrets."
} else { Write-Host ".env already exists - left untouched." }
if (-not (Test-Path "frontend\.env")) { Copy-Item "frontend\.env.example" "frontend\.env" }

Write-Host "`n== Backend dependencies ==" -ForegroundColor Cyan
if (-not (Test-Path "backend\.venv")) { python -m venv backend\.venv }
& "backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements-dev.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed - see the message above." -ForegroundColor Red; exit 1 }

Write-Host "`n== Frontend dependencies ==" -ForegroundColor Cyan
Push-Location frontend
npm install
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "npm install failed - see the message above." -ForegroundColor Red; exit 1 }
Pop-Location

Write-Host "`nSetup complete. Next: scripts\start.ps1   (or scripts\start.ps1 -Docker)" -ForegroundColor Green
