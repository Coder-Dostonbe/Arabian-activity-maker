//! A small rotating log file in the app's log directory.
//!
//! `arabmorph-service.log` grows to `MAX_BYTES`, then becomes `.1` (older files
//! shift to `.2`, `.3`; the oldest is dropped). Logging never fails the caller.

use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

const MAX_BYTES: u64 = 1024 * 1024;
const KEEP: usize = 3;

pub struct Log {
    dir: PathBuf,
    path: PathBuf,
    file: Mutex<Option<File>>,
}

impl Log {
    pub fn new(dir: PathBuf, name: &str) -> Self {
        let path = dir.join(name);
        Log { dir, path, file: Mutex::new(None) }
    }

    pub fn dir(&self) -> &Path {
        let _ = fs::create_dir_all(&self.dir);
        &self.dir
    }

    pub fn write(&self, source: &str, message: &str) {
        let Ok(mut guard) = self.file.lock() else { return };
        if guard.is_none() || self.too_big() {
            *guard = None;
            if self.too_big() {
                self.rotate();
            }
            let _ = fs::create_dir_all(&self.dir);
            *guard = OpenOptions::new().create(true).append(true).open(&self.path).ok();
        }
        if let Some(file) = guard.as_mut() {
            let _ = writeln!(file, "{} [{source}] {message}", timestamp());
        }
    }

    fn too_big(&self) -> bool {
        fs::metadata(&self.path).map(|m| m.len() >= MAX_BYTES).unwrap_or(false)
    }

    fn rotate(&self) {
        let numbered = |n: usize| self.path.with_extension(format!("log.{n}"));
        let _ = fs::remove_file(numbered(KEEP));
        for n in (1..KEEP).rev() {
            let _ = fs::rename(numbered(n), numbered(n + 1));
        }
        let _ = fs::rename(&self.path, numbered(1));
    }
}

/// UTC time as `YYYY-MM-DD HH:MM:SS`, without a date crate.
pub fn timestamp() -> String {
    let secs = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let (days, rem) = (secs / 86_400, secs % 86_400);
    let (y, m, d) = civil_from_days(days as i64);
    format!("{y:04}-{m:02}-{d:02} {:02}:{:02}:{:02}Z", rem / 3600, rem % 3600 / 60, rem % 60)
}

/// Howard Hinnant's days-to-civil algorithm.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (yoe + era * 400 + i64::from(m <= 2), m, d)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn civil_dates() {
        assert_eq!(civil_from_days(0), (1970, 1, 1));
        assert_eq!(civil_from_days(20_755), (2026, 10, 29));
        assert_eq!(civil_from_days(11_016), (2000, 2, 29));
    }

    #[test]
    fn rotates_and_keeps_three_files() {
        let dir = std::env::temp_dir().join(format!("am-log-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        let log = Log::new(dir.clone(), "t.log");
        let line = "x".repeat(1000);
        for _ in 0..5000 {
            log.write("test", &line);
        }
        assert!(dir.join("t.log").exists());
        assert!(dir.join("t.log.1").exists() && dir.join("t.log.3").exists());
        assert!(!dir.join("t.log.4").exists());
        assert!(fs::metadata(dir.join("t.log")).unwrap().len() <= MAX_BYTES + 2000);
        let _ = fs::remove_dir_all(&dir);
    }
}
