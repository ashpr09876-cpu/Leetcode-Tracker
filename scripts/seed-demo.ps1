<# OPTIONAL: adds a clearly labelled demo account (demo@codetrack.local) with [DEMO] sample problems. #>
$root = Split-Path -Parent $PSScriptRoot
Push-Location "$root\backend"
& ".venv\Scripts\python.exe" seed_demo.py
Pop-Location
