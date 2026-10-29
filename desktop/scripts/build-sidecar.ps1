# Builds the Python engine service into a folder that Tauri bundles as a resource.
# Output: desktop/src-tauri/binaries/arabmorph-service/arabmorph-service.exe (+ _internal/)
# --onedir starts faster than --onefile (nothing is unpacked on each start) and
# trips fewer antivirus heuristics.
# Native tools write progress to stderr; failures are detected via $LASTEXITCODE.
$ErrorActionPreference = "Continue"
$root = Resolve-Path "$PSScriptRoot\..\.."
$python = Join-Path $root ".venv\Scripts\python.exe"
$name = "arabmorph-service"
$work = Join-Path $root "desktop\build\sidecar"
$bin = Join-Path $root "desktop\src-tauri\binaries"

& $python -c "import PyInstaller" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { & $python -m pip install -q "pyinstaller>=6" }

# The old --onefile build (arabmorph-service-<triple>.exe) is no longer used.
Get-ChildItem $bin -Filter "$name-*.exe" -ErrorAction SilentlyContinue | Remove-Item -Force

& $python -m PyInstaller `
    --noconfirm --clean --onedir --console `
    --name $name `
    --paths (Join-Path $root "engine\src") `
    --add-data "$(Join-Path $root 'engine\src\arabmorph\data\lexicon_*.json');arabmorph\data" `
    --distpath $bin --workpath $work --specpath $work `
    (Join-Path $root "desktop\sidecar\arabmorph_service.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# Smoke test the frozen service over stdio.
$exe = Join-Path $bin "$name\$name.exe"
$reply = '{"id":1,"op":"version"}' | & $exe
if ($LASTEXITCODE -ne 0 -or $reply -notmatch '"ok": true') { throw "sidecar smoke test failed: $reply" }
Write-Host "sidecar OK: $reply"
