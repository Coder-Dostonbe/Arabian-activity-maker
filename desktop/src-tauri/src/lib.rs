//! Desktop shell: runs the bundled Python engine service and forwards requests.
//!
//! The service talks newline-delimited JSON over stdin/stdout. No network port
//! is opened, so only this process can reach the engine.

use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;

use serde_json::Value;
use tauri::{Manager, RunEvent, State};

/// Name of the sidecar next to the app executable (Tauri strips the target triple when bundling).
const SERVICE_EXE: &str = "arabmorph-service.exe";

struct Service {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

#[derive(Default)]
struct Engine(Mutex<Option<Service>>);

fn service_path() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| format!("cannot locate application: {e}"))?;
    let dir = exe.parent().ok_or("application has no parent directory")?;
    Ok(dir.join(SERVICE_EXE))
}

fn spawn() -> Result<Service, String> {
    let path = service_path()?;
    let mut cmd = Command::new(&path);
    cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    let mut child = cmd
        .spawn()
        .map_err(|e| format!("cannot start engine service at {}: {e}", path.display()))?;
    let stdin = child.stdin.take().ok_or("engine service has no stdin")?;
    let stdout = BufReader::new(child.stdout.take().ok_or("engine service has no stdout")?);
    Ok(Service { child, stdin, stdout })
}

fn roundtrip(service: &mut Service, request: &Value) -> Result<Value, String> {
    let line = serde_json::to_string(request).map_err(|e| e.to_string())?;
    service
        .stdin
        .write_all(line.as_bytes())
        .and_then(|_| service.stdin.write_all(b"\n"))
        .and_then(|_| service.stdin.flush())
        .map_err(|e| format!("engine service is not accepting requests: {e}"))?;
    let mut reply = String::new();
    let read = service
        .stdout
        .read_line(&mut reply)
        .map_err(|e| format!("engine service did not reply: {e}"))?;
    if read == 0 {
        return Err("engine service stopped".into());
    }
    serde_json::from_str(&reply).map_err(|e| format!("engine service sent an invalid reply: {e}"))
}

/// Forward one request to the engine. Restarts the service once if it has died.
#[tauri::command(async)]
fn engine_call(engine: State<'_, Engine>, request: Value) -> Result<Value, String> {
    if !request.is_object() {
        return Err("request must be a JSON object".into());
    }
    let mut guard = engine.0.lock().map_err(|_| "engine state is unavailable")?;
    let mut last_error = String::new();
    for _ in 0..2 {
        if guard.is_none() {
            *guard = Some(spawn()?);
        }
        let service = guard.as_mut().expect("service was just started");
        match roundtrip(service, &request) {
            Ok(value) => return Ok(value),
            Err(e) => {
                last_error = e;
                if let Some(mut dead) = guard.take() {
                    let _ = dead.child.kill();
                }
            }
        }
    }
    Err(last_error)
}

pub fn run() {
    let app = tauri::Builder::default()
        .manage(Engine::default())
        .setup(|app| {
            // Start the service in the background so the first request does not wait for it.
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let engine = handle.state::<Engine>();
                if let Ok(mut guard) = engine.0.lock() {
                    if guard.is_none() {
                        *guard = spawn().ok();
                    }
                };
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![engine_call])
        .build(tauri::generate_context!())
        .expect("error while building ArabMorph AI");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Ok(mut guard) = handle.state::<Engine>().0.lock() {
                if let Some(mut service) = guard.take() {
                    let _ = service.child.kill();
                }
            };
        }
    });
}
