//! Desktop shell: runs the bundled Python engine service and forwards requests.
//!
//! The service talks newline-delimited JSON over stdin/stdout. No network port
//! is opened, so only this process can reach the engine. The shell also owns
//! everything the webview must not do itself: the app's data files, the
//! service log, the Anthropic API key (Windows Credential Manager) and the
//! optional Claude request.

mod claude;
mod log;
mod store;

use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::mpsc::{self, Receiver, RecvTimeoutError};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use serde_json::Value;
use tauri::{AppHandle, Manager, RunEvent, State};

use crate::log::Log;

/// The service directory inside the app's resources (PyInstaller --onedir output).
const SERVICE_DIR: &str = "arabmorph-service";
const SERVICE_EXE: &str = "arabmorph-service.exe";
const TIMEOUT: Duration = Duration::from_secs(15);
const IMPORT_TIMEOUT: Duration = Duration::from_secs(60);

struct Service {
    child: Child,
    stdin: ChildStdin,
    replies: Receiver<String>,
}

impl Service {
    fn kill(mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[derive(Default)]
struct Engine(Mutex<Option<Service>>);

fn service_path(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("cannot locate application resources: {e}"))?;
    Ok(dir.join(SERVICE_DIR).join(SERVICE_EXE))
}

fn spawn(app: &AppHandle) -> Result<Service, String> {
    let log = app.state::<Arc<Log>>().inner().clone();
    let path = service_path(app)?;
    let mut cmd = Command::new(&path);
    // The teacher's own lexicon entries live next to the other data files.
    if let Ok(data) = app.path().app_data_dir() {
        cmd.env("ARABMORPH_USER_LEXICON", data.join("data").join("lexicon_user.json"));
    }
    start(cmd, log).map_err(|e| format!("{e} ({})", path.display()))
}

fn start(mut cmd: Command, log: Arc<Log>) -> Result<Service, String> {
    cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    let mut child = cmd.spawn().map_err(|e| {
        let message = format!("cannot start engine service: {e}");
        log.write("shell", &message);
        message
    })?;
    let stdin = child.stdin.take().ok_or("engine service has no stdin")?;
    let stdout = child.stdout.take().ok_or("engine service has no stdout")?;
    let stderr = child.stderr.take().ok_or("engine service has no stderr")?;

    // Replies are read on their own thread so a request can wait with a timeout.
    let (tx, replies) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if tx.send(line).is_err() {
                break;
            }
        }
    });
    let service_log = log.clone();
    std::thread::spawn(move || {
        for line in BufReader::new(stderr).lines().map_while(Result::ok) {
            service_log.write("service", &line);
        }
    });
    log.write("shell", &format!("engine service started (pid {})", child.id()));
    Ok(Service { child, stdin, replies })
}

enum Failure {
    /// The service is gone or unusable; a fresh one may succeed.
    Dead(String),
    /// The service did not answer in time; retrying the same request would likely hang again.
    Timeout(String),
}

fn roundtrip(service: &mut Service, request: &Value, timeout: Duration) -> Result<Value, Failure> {
    let line = serde_json::to_string(request).map_err(|e| Failure::Dead(e.to_string()))?;
    service
        .stdin
        .write_all(line.as_bytes())
        .and_then(|_| service.stdin.write_all(b"\n"))
        .and_then(|_| service.stdin.flush())
        .map_err(|e| Failure::Dead(format!("engine service is not accepting requests: {e}")))?;
    let id = request.get("id");
    loop {
        let reply = match service.replies.recv_timeout(timeout) {
            Ok(reply) => reply,
            Err(RecvTimeoutError::Timeout) => {
                return Err(Failure::Timeout(format!(
                    "engine service did not reply within {} s",
                    timeout.as_secs()
                )))
            }
            Err(RecvTimeoutError::Disconnected) => return Err(Failure::Dead("engine service stopped".into())),
        };
        let value: Value = serde_json::from_str(&reply)
            .map_err(|e| Failure::Dead(format!("engine service sent an invalid reply: {e}")))?;
        // A late reply to an earlier request is skipped, never returned for this one.
        if value.get("id") == id {
            return Ok(value);
        }
    }
}

/// Forward one request to the engine. Restarts the service once if it has died;
/// on a timeout the service is killed (it restarts on the next request) and an error is returned.
#[tauri::command(async)]
fn engine_call(app: AppHandle, engine: State<'_, Engine>, log: State<'_, Arc<Log>>, request: Value) -> Result<Value, String> {
    if !request.is_object() {
        return Err("request must be a JSON object".into());
    }
    let timeout = if request.get("op").and_then(Value::as_str) == Some("import_file") { IMPORT_TIMEOUT } else { TIMEOUT };
    let mut guard = engine.0.lock().map_err(|_| "engine state is unavailable")?;
    let mut last_error = String::new();
    for _ in 0..2 {
        if guard.is_none() {
            *guard = Some(spawn(&app)?);
        }
        let service = guard.as_mut().expect("service was just started");
        match roundtrip(service, &request, timeout) {
            Ok(value) => return Ok(value),
            Err(Failure::Timeout(e)) => {
                log.write("shell", &format!("{e}; restarting the service"));
                if let Some(stuck) = guard.take() {
                    stuck.kill();
                }
                return Err(e);
            }
            Err(Failure::Dead(e)) => {
                log.write("shell", &e);
                last_error = e;
                if let Some(dead) = guard.take() {
                    dead.kill();
                }
            }
        }
    }
    Err(last_error)
}

/// Show the folder that holds the service log in Explorer.
#[tauri::command]
fn open_log_folder(log: State<'_, Arc<Log>>) -> Result<(), String> {
    Command::new("explorer")
        .arg(log.dir())
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("cannot open the log folder: {e}"))
}

pub fn run() {
    let app = tauri::Builder::default()
        .manage(Engine::default())
        .setup(|app| {
            let log_dir = app.path().app_log_dir()?;
            app.manage(Arc::new(Log::new(log_dir, "arabmorph-service.log")));
            app.manage(store::Store::new(app.path().app_data_dir()?));
            // Start the service in the background so the first request does not wait for it.
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let engine = handle.state::<Engine>();
                if let Ok(mut guard) = engine.0.lock() {
                    if guard.is_none() {
                        *guard = spawn(&handle).ok();
                    }
                };
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            engine_call,
            open_log_folder,
            store::store_load,
            store::store_save,
            store::backup_export,
            claude::api_key_status,
            claude::api_key_forget,
            claude::api_key_save,
            claude::claude_draft,
            claude::claude_lexicon,
            store::export_file,
        ])
        .build(tauri::generate_context!())
        .expect("error while building ArabMorph AI");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Ok(mut guard) = handle.state::<Engine>().0.lock() {
                if let Some(service) = guard.take() {
                    service.kill();
                }
            };
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    /// A stand-in service: the repository's Python running a one-line script.
    fn fake(script: &str, tag: &str) -> Service {
        let python = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../.venv/Scripts/python.exe");
        let mut cmd = Command::new(python);
        cmd.args(["-I", "-c", script]);
        let dir = std::env::temp_dir().join(format!("am-shell-{tag}-{}", std::process::id()));
        start(cmd, Arc::new(Log::new(dir, "t.log"))).expect("python starts")
    }

    #[test]
    fn a_silent_service_times_out() {
        let mut service = fake("import time; time.sleep(30)", "silent");
        let started = std::time::Instant::now();
        let result = roundtrip(&mut service, &json!({"id": 1, "op": "version"}), Duration::from_millis(500));
        assert!(matches!(result, Err(Failure::Timeout(_))));
        assert!(started.elapsed() < Duration::from_secs(5));
        service.kill();
    }

    #[test]
    fn a_late_reply_to_another_request_is_skipped() {
        let script = "import sys; sys.stdin.readline(); print('{\"id\": 0}'); print('{\"id\": 1, \"ok\": true}'); sys.stdout.flush()";
        let mut service = fake(script, "late");
        let reply = roundtrip(&mut service, &json!({"id": 1}), Duration::from_secs(10)).ok().expect("reply");
        assert_eq!(reply["ok"], true);
        service.kill();
    }

    #[test]
    fn a_service_that_exits_is_dead() {
        let mut service = fake("pass", "dead");
        let result = roundtrip(&mut service, &json!({"id": 1}), Duration::from_secs(10));
        assert!(matches!(result, Err(Failure::Dead(_))));
    }
}
