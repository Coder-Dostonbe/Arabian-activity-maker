# Builds the Python engine service into a single .exe for Tauri's externalBin.
# Output: desktop/src-tauri/binaries/arabmorph-service-<target-triple>.exe
# Native tools write progress to stderr; failures are detected via $LASTEXITCODE.
$ErrorActionPreference = "Continue"
$root = Resolve-Path "$PSScriptRoot\..\.."
$python = Join-Path $root ".venv\Scripts\python.exe"
$triple = "x86_64-pc-windows-msvc"
$work = Join-Path $root "desktop\build\sidecar"
$bin = Join-Path $root "desktop\src-tauri\binaries"

& $python -c "import PyInstaller" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { & $python -m pip install -q "pyinstaller>=6" }

& $python -m PyInstaller `
    --noconfirm --clean --onefile --console `
    --name "arabmorph-service-$triple" `
    --paths (Join-Path $root "engine\src") `
    --add-data "$(Join-Path $root 'engine\src\arabmorph\data\lexicon_*.json');arabmorph\data" `
    --distpath $bin --workpath $work --specpath $work `
    (Join-Path $root "desktop\sidecar\arabmorph_service.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# Smoke test the frozen binary over stdio.
$exe = Join-Path $bin "arabmorph-service-$triple.exe"
$reply = '{"id":1,"op":"version"}' | & $exe
if ($LASTEXITCODE -ne 0 -or $reply -notmatch '"ok": true') { throw "sidecar smoke test failed: $reply" }
Write-Host "sidecar OK: $reply"

