//! Optional online assistant: drafts activity items with Claude using the teacher's own API key.
//!
//! The key lives in Windows Credential Manager and never goes back to the
//! webview; the HTTP request is made here, so the webview needs no network
//! access at all. The reply's items are returned raw; the UI cleans them.

use std::time::Duration;

use serde_json::{json, Value};

const URL: &str = "https://api.anthropic.com/v1/messages";
const MAX_ITEMS: u64 = 40;
const KEYRING_SERVICE: &str = "ArabMorph AI";
const KEYRING_USER: &str = "anthropic-api-key";
const REQUEST_TIMEOUT: Duration = Duration::from_secs(300);

const SYSTEM: &str = "You write classroom exercise items for students learning Arabic morphology and grammar \
(singular, dual and plural forms, case endings, the definite article, iḍāfa).

Each item is shown to the whole class on a screen:
- prompt: the Arabic word or a short question.
- answer: the single correct answer. Write Arabic with full diacritics.
- note: a short hint in the requested interface language, e.g. which form is asked for.
- options: three wrong answers a student could plausibly confuse with the correct one, such as the same word \
in another case or number. Never repeat the correct answer among them.

Correctness matters more than variety: leave out any item whose answer you are not certain of, \
and avoid words whose form depends on a meaning the prompt does not state.";

fn schema() -> Value {
    json!({
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "prompt": { "type": "string" },
                        "answer": { "type": "string" },
                        "note": { "type": "string" },
                        "options": { "type": "array", "items": { "type": "string" } }
                    },
                    "required": ["prompt", "answer", "note", "options"],
                    "additionalProperties": false
                }
            }
        },
        "required": ["items"],
        "additionalProperties": false
    })
}

/// An error the UI shows by kind: auth / rate / network / refusal / invalid / other.
fn failure(kind: &str, message: impl Into<String>) -> Value {
    json!({ "kind": kind, "message": message.into() })
}

fn entry() -> Result<keyring::Entry, Value> {
    keyring::Entry::new(KEYRING_SERVICE, KEYRING_USER)
        .map_err(|e| failure("other", format!("Credential Manager is unavailable: {e}")))
}

fn stored_key() -> Option<String> {
    entry().ok()?.get_password().ok().filter(|k| !k.is_empty())
}

/// Whether a key is saved in Credential Manager (the key itself is never returned).
#[tauri::command]
pub fn api_key_status() -> bool {
    stored_key().is_some()
}

/// Save a key without using it (moves a key kept by an older version out of the webview's storage).
#[tauri::command]
pub fn api_key_save(key: String) -> Result<(), Value> {
    let key = key.trim();
    if key.is_empty() || key.len() > 500 {
        return Err(failure("auth", ""));
    }
    entry()?.set_password(key).map_err(|e| failure("other", format!("cannot save the key: {e}")))
}

#[tauri::command]
pub fn api_key_forget() -> Result<(), Value> {
    match entry()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(failure("other", format!("cannot remove the saved key: {e}"))),
    }
}

/// The models the teacher can choose from; the cheapest is the default in the UI.
/// Server-side refusal fallback exists for Opus and Sonnet only.
const MODELS: &[(&str, bool)] = &[("claude-haiku-5-5", false), ("claude-sonnet-5-5", true), ("claude-opus-5-5", true)];

fn model(name: Option<String>) -> Result<(&'static str, bool), Value> {
    let name = name.unwrap_or_else(|| MODELS[0].0.to_string());
    MODELS
        .iter()
        .find(|(id, _)| *id == name)
        .copied()
        .ok_or_else(|| failure("other", format!("unknown model {name:?}")))
}

/// The key to use: a typed one (saved when `remember`), else the saved one. Unchecking `remember` removes the saved key.
fn resolve_key(key: Option<String>, remember: bool) -> Result<String, Value> {
    let typed = key.map(|k| k.trim().to_string()).filter(|k| !k.is_empty());
    let key = typed.clone().or_else(stored_key).ok_or_else(|| failure("auth", ""))?;
    if remember {
        if let Some(k) = &typed {
            entry()?.set_password(k).map_err(|e| failure("other", format!("cannot save the key: {e}")))?;
        }
    } else {
        api_key_forget()?;
    }
    Ok(key)
}

/// One structured-output request; returns the parsed JSON object Claude wrote.
fn ask(key: &str, model: (&str, bool), system: &str, user: String, schema: Value) -> Result<Value, Value> {
    let (id, fallback) = model;
    let mut body = json!({
        "model": id,
        "max_tokens": 16000,
        "output_config": { "effort": "medium", "format": { "type": "json_schema", "schema": schema } },
        "system": system,
        "messages": [{ "role": "user", "content": user }],
    });
    if fallback {
        // Opt in to server-side fallback: if a safety classifier declines, the API retries on its recommended model.
        body["fallbacks"] = json!("default");
    }
    let response = send(key, &body.to_string(), fallback)?;
    if response.get("stop_reason").and_then(Value::as_str) == Some("refusal") {
        return Err(failure("refusal", ""));
    }
    let text = response
        .get("content")
        .and_then(Value::as_array)
        .and_then(|blocks| blocks.iter().find(|b| b.get("type").and_then(Value::as_str) == Some("text")))
        .and_then(|b| b.get("text"))
        .and_then(Value::as_str)
        .ok_or_else(|| failure("invalid", ""))?;
    serde_json::from_str(text).map_err(|_| failure("invalid", ""))
}

/// Ask Claude for `count` items on `topic` with the chosen `model_id`.
#[tauri::command(async)]
pub fn claude_draft(
    key: Option<String>,
    remember: bool,
    topic: String,
    count: u64,
    language: String,
    model_id: Option<String>,
) -> Result<Value, Value> {
    let model = model(model_id)?;
    let key = resolve_key(key, remember)?;
    let topic: String = topic.trim().chars().take(2000).collect();
    let language: String = language.chars().take(40).collect();
    let user = format!(
        "Topic: {topic}\nNumber of items: {}\nInterface language for prompts and notes: {language}",
        count.clamp(1, MAX_ITEMS)
    );
    let parsed = ask(&key, model, SYSTEM, user, schema())?;
    match parsed.get("items") {
        Some(items) if items.is_array() => Ok(items.clone()),
        _ => Err(failure("invalid", "")),
    }
}

const LEXICON_SYSTEM: &str = "You describe one Arabic noun or adjective for a morphology engine's lexicon. \
Give its singular lemma fully vocalised, without the article and without case endings (كِتَاب, not كِتَابٌ). \
Report only what you are confident of: gender, the class of its final letter (sound, maqsur, manqus, mamdud), \
for a trilateral maqsur noun whether its alif comes from waw or yeh, for a mamdud noun the type of its final hamza, \
whether the singular is diptote (ممنوع من الصرف), and the plural(s) in actual use. A broken plural must be written \
fully vocalised; a sound plural has an empty form. If the word is not a noun or adjective, or you are not sure \
of it, say so in `note` and leave `plurals` empty.";

fn lexicon_schema() -> Value {
    let one_of = |values: &[&str]| json!({ "type": "string", "enum": values });
    json!({
        "type": "object",
        "properties": {
            "lemma": { "type": "string" },
            "pos": one_of(&["noun", "adjective", "proper_noun"]),
            "gender": one_of(&["masculine", "feminine", "unknown"]),
            "final_class": one_of(&["sound", "maqsur", "manqus", "mamdud"]),
            "alif_origin": one_of(&["", "waw", "yeh"]),
            "hamza_type": one_of(&["", "original", "feminine", "substituted", "ilhaq"]),
            "diptote": { "type": "boolean" },
            "gloss_en": { "type": "string" },
            "plurals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": one_of(&["sound_masculine", "sound_feminine", "broken"]),
                        "form": { "type": "string" },
                        "diptote": { "type": "boolean" }
                    },
                    "required": ["kind", "form", "diptote"],
                    "additionalProperties": false
                }
            },
            "note": { "type": "string" }
        },
        "required": ["lemma", "pos", "gender", "final_class", "alif_origin", "hamza_type", "diptote", "gloss_en", "plurals", "note"],
        "additionalProperties": false
    })
}

/// Ask Claude to describe `word` as a lexicon entry. The proposal is returned for the teacher's review,
/// never stored here.
#[tauri::command(async)]
pub fn claude_lexicon(key: Option<String>, remember: bool, word: String, model_id: Option<String>) -> Result<Value, Value> {
    let model = model(model_id)?;
    let key = resolve_key(key, remember)?;
    let word: String = word.trim().chars().take(64).collect();
    if word.is_empty() {
        return Err(failure("invalid", ""));
    }
    ask(&key, model, LEXICON_SYSTEM, format!("Word: {word}"), lexicon_schema())
}

/// POST with one retry on a connection failure, an overloaded API or a server error.
fn send(key: &str, body: &str, fallback: bool) -> Result<Value, Value> {
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(REQUEST_TIMEOUT))
        .http_status_as_error(false)
        .build()
        .into();
    let mut last = failure("network", "");
    for attempt in 0..2 {
        if attempt > 0 {
            std::thread::sleep(Duration::from_secs(2));
        }
        let mut request = agent
            .post(URL)
            .header("x-api-key", key)
            .header("anthropic-version", "2023-06-01")
            .header("content-type", "application/json");
        if fallback {
            request = request.header("anthropic-beta", "server-side-fallback-2026-07-01");
        }
        let mut response = match request.send(body) {
            Ok(r) => r,
            Err(e) => {
                last = failure("network", e.to_string());
                continue;
            }
        };
        let status = response.status().as_u16();
        let text = response.body_mut().read_to_string().unwrap_or_default();
        let value: Value = serde_json::from_str(&text).unwrap_or(Value::Null);
        let message = value.pointer("/error/message").and_then(Value::as_str).unwrap_or("").to_string();
        match status {
            200..=299 => return Ok(value),
            401 | 403 => return Err(failure("auth", "")),
            429 => return Err(failure("rate", "")),
            500..=599 => last = failure("other", message),
            _ => return Err(failure("other", message)),
        }
    }
    Err(last)
}
