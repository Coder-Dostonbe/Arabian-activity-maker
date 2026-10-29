//! The app's data files (word sets, settings) in the app data directory.
//!
//! A save writes a temporary file, flushes it to disk and renames it over the
//! old one, so a crash never leaves half a file. Before each save the previous
//! version is copied to `backups/`, and the newest `BACKUPS` copies are kept.
//! If the main file cannot be read, the newest readable backup is returned.

use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::{json, Value};
use tauri::State;

const NAMES: &[&str] = &["sets", "settings"];
const BACKUPS: usize = 5;
const MAX_BYTES: usize = 32 * 1024 * 1024;

pub struct Store {
    dir: PathBuf,
}

impl Store {
    pub fn new(app_data: PathBuf) -> Self {
        Store { dir: app_data.join("data") }
    }

    fn path(&self, name: &str) -> Result<PathBuf, String> {
        if !NAMES.contains(&name) {
            return Err(format!("unknown data file {name:?}"));
        }
        Ok(self.dir.join(format!("{name}.json")))
    }

    fn backups(&self, name: &str) -> Vec<PathBuf> {
        let prefix = format!("{name}-");
        let mut found: Vec<PathBuf> = fs::read_dir(self.dir.join("backups"))
            .map(|entries| {
                entries
                    .filter_map(|e| e.ok().map(|e| e.path()))
                    .filter(|p| {
                        p.file_name().and_then(|n| n.to_str()).is_some_and(|n| n.starts_with(&prefix) && n.ends_with(".json"))
                    })
                    .collect()
            })
            .unwrap_or_default();
        found.sort(); // names carry a zero-padded timestamp: oldest first
        found
    }

    pub fn load(&self, name: &str) -> Result<Value, String> {
        let path = self.path(name)?;
        if let Some(contents) = read_json(&path) {
            return Ok(json!({ "contents": contents, "recovered": false }));
        }
        let had_file = path.exists();
        for backup in self.backups(name).iter().rev() {
            if let Some(contents) = read_json(backup) {
                return Ok(json!({ "contents": contents, "recovered": had_file }));
            }
        }
        Ok(json!({ "contents": null, "recovered": false }))
    }

    pub fn save(&self, name: &str, contents: &str) -> Result<(), String> {
        let path = self.path(name)?;
        if contents.len() > MAX_BYTES {
            return Err("data is too large to save".into());
        }
        serde_json::from_str::<Value>(contents).map_err(|e| format!("refusing to save invalid JSON: {e}"))?;
        let backups = self.dir.join("backups");
        fs::create_dir_all(&backups).map_err(|e| format!("cannot create the data folder: {e}"))?;

        if read_json(&path).is_some() {
            let millis = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis()).unwrap_or(0);
            let _ = fs::copy(&path, backups.join(format!("{name}-{millis:015}.json")));
            let all = self.backups(name);
            for old in all.iter().take(all.len().saturating_sub(BACKUPS)) {
                let _ = fs::remove_file(old);
            }
        }
        write_atomic(&path, contents.as_bytes()).map_err(|e| format!("cannot save {name}: {e}"))
    }
}

fn read_json(path: &Path) -> Option<String> {
    let text = fs::read_to_string(path).ok()?;
    serde_json::from_str::<Value>(&text).ok()?;
    Some(text)
}

fn write_atomic(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let tmp = path.with_extension("json.tmp");
    {
        let mut file = File::create(&tmp)?;
        file.write_all(bytes)?;
        file.sync_all()?;
    }
    // On Windows, std::fs::rename replaces an existing file (MoveFileEx with REPLACE_EXISTING).
    fs::rename(&tmp, path)
}

#[tauri::command(async)]
pub fn store_load(store: State<'_, Store>, name: String) -> Result<Value, String> {
    store.load(&name)
}

#[tauri::command(async)]
pub fn store_save(store: State<'_, Store>, name: String, contents: String) -> Result<(), String> {
    store.save(&name, &contents)
}

/// Write an "Export all" backup to the Downloads folder and show it in Explorer; returns its path.
#[tauri::command(async)]
pub fn backup_export(app: tauri::AppHandle, contents: String) -> Result<String, String> {
    use tauri::Manager;
    serde_json::from_str::<Value>(&contents).map_err(|e| format!("invalid backup: {e}"))?;
    let dir = app.path().download_dir().map_err(|e| format!("cannot find the Downloads folder: {e}"))?;
    fs::create_dir_all(&dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    let stamp = crate::log::timestamp().replace([':', ' '], "-").trim_end_matches('Z').to_string();
    let path = dir.join(format!("ArabMorph-backup-{stamp}.json"));
    write_atomic(&path, contents.as_bytes()).map_err(|e| format!("cannot write {}: {e}", path.display()))?;
    let _ = std::process::Command::new("explorer").arg(format!("/select,{}", path.display())).spawn();
    Ok(path.display().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_store(tag: &str) -> (Store, PathBuf) {
        let dir = std::env::temp_dir().join(format!("am-store-{tag}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        (Store::new(dir.clone()), dir)
    }

    #[test]
    fn saves_loads_and_keeps_five_backups() {
        let (store, dir) = temp_store("backups");
        assert_eq!(store.load("sets").unwrap()["contents"], Value::Null);
        for i in 0..8 {
            store.save("sets", &format!("[{i}]")).unwrap();
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
        assert_eq!(store.load("sets").unwrap()["contents"], "[7]");
        let backups = store.backups("sets");
        assert_eq!(backups.len(), BACKUPS);
        assert_eq!(fs::read_to_string(backups.last().unwrap()).unwrap(), "[6]");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_corrupt_file_falls_back_to_the_newest_backup() {
        let (store, dir) = temp_store("corrupt");
        store.save("settings", r#"{"a":1}"#).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(2));
        store.save("settings", r#"{"a":2}"#).unwrap();
        fs::write(store.path("settings").unwrap(), "{truncated").unwrap();
        let loaded = store.load("settings").unwrap();
        assert_eq!(loaded["contents"], r#"{"a":1}"#);
        assert_eq!(loaded["recovered"], true);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn rejects_unknown_names_and_invalid_json() {
        let (store, dir) = temp_store("reject");
        assert!(store.save("../evil", "{}").is_err());
        assert!(store.save("sets", "not json").is_err());
        assert!(!store.dir.join("sets.json").exists());
        let _ = fs::remove_dir_all(&dir);
    }
}
