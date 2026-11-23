<# Runs backend tests (SQLite in-memory, no Docker needed) and frontend tests.  Add -E2E to run Playwright (stack must be running). #>
param([switch]$E2E)
$root = Split-Path -Parent $PSScriptRoot
$failed = $false
Push-Location "$root\backend"
& ".venv\Scripts\python.exe" -m pytest -q
if ($LASTEXITCODE -ne 0) { $failed = $true }
Pop-Location
Push-Location "$root\frontend"
npm test
if ($LASTEXITCODE -ne 0) { $failed = $true }
npm run build
if ($LASTEXITCODE -ne 0) { $failed = $true }
if ($E2E) { npx playwright install chromium; npx playwright test; if ($LASTEXITCODE -ne 0) { $failed = $true } }
Pop-Location
if ($failed) { Write-Host "`nSome checks FAILED." -ForegroundColor Red; exit 1 } else { Write-Host "`nAll checks passed." -ForegroundColor Green }
