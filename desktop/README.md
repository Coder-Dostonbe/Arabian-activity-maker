# ArabMorph AI — Windows desktop app

Tauri 2 + Vue 3 + TypeScript shell around the offline `arabmorph` engine.

```
desktop/
├── src/                    # Vue UI (Uzbek interface, Arabic RTL content)
├── sidecar/                # Python stdio service wrapping the engine
│   └── tests/
├── scripts/build-sidecar.ps1   # PyInstaller → src-tauri/binaries/arabmorph-service-<triple>.exe
└── src-tauri/              # Rust shell: spawns the service, exposes `engine_call`
```

## How it works

The Rust shell starts `arabmorph-service.exe` (the engine frozen with
PyInstaller) as a hidden child process. The two talk newline-delimited JSON
over stdin/stdout. **No network port is opened and nothing goes online.** The
service validates every request itself rather than trusting the UI. If the
service dies, the shell restarts it once on the next request.

The installer includes the service, so end users don't need Python.

## Build requirements (development machine only)

- Python venv at the repo root with the engine installed (`pip install -e "engine[dev]"`)
- Node.js 18+
- Rust (stable, MSVC toolchain) and Visual Studio C++ Build Tools
- WebView2 runtime (preinstalled on Windows 10/11)

## Build

```powershell
cd desktop
npm install
npm run sidecar          # freeze the engine service (PyInstaller) and smoke-test it
npx tauri build          # → src-tauri/target/release/bundle/nsis/ArabMorph AI_0.2.0_x64-setup.exe
```

`npx tauri dev` runs the app with hot reload. Run `npm run sidecar` first, and
again whenever the engine changes.

## Tests

```powershell
..\.venv\Scripts\python -m pytest sidecar/tests   # service protocol + validation
npm run build                                      # vue-tsc type check + production build
```

## Installer notes

- NSIS, per-user install (`installMode: currentUser`): no administrator rights needed.
- The installer is **not code-signed**, so Windows SmartScreen may warn on
  first run ("More info → Run anyway"). Signing needs a certificate, which
  must never be committed (`.gitignore` excludes `*.pfx`, `*.p12`, `*.key`).
