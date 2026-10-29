// The app's saved data: word sets and settings, as JSON files in the app data folder.
// The Rust shell writes them atomically and keeps the last 5 versions as backups.
// Saves are debounced; outside the desktop app (plain `vite` in a browser) localStorage is used instead.
import { invoke, isTauri } from "@tauri-apps/api/core";
import { ref } from "vue";

type Name = "sets" | "settings";

const SAVE_DELAY = 500;
const PREFIX = "arabmorph.";
const LEGACY_SETS = "arabmorph.sets.v1";
const LEGACY_KEY = "arabmorph.claude.key"; // an older version kept the API key here, in plain text

let settings: Record<string, unknown> = {};
let sets: unknown[] | null = null;
const timers: Partial<Record<Name, ReturnType<typeof setTimeout>>> = {};

/** The last save failed (shown as a warning; the next change retries). */
export const saveFailed = ref(false);
/** A data file was unreadable and its newest backup was loaded instead. */
export const recovered = ref(false);

interface Loaded {
  contents: string | null;
  recovered: boolean;
}

async function load(name: Name): Promise<unknown> {
  let loaded: Loaded;
  if (isTauri()) {
    loaded = await invoke<Loaded>("store_load", { name });
  } else {
    loaded = { contents: localStorageGet(`${PREFIX}file.${name}`), recovered: false };
  }
  if (loaded.recovered) recovered.value = true;
  return loaded.contents === null ? null : JSON.parse(loaded.contents);
}

async function write(name: Name, value: unknown): Promise<void> {
  const contents = JSON.stringify(value);
  if (isTauri()) await invoke("store_save", { name, contents });
  else localStorage.setItem(`${PREFIX}file.${name}`, contents);
}

function localStorageGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

/** Every `arabmorph.*` value an older version kept in localStorage, except the sets and the key. */
function legacySettings(): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key?.startsWith(PREFIX) || key === LEGACY_SETS || key === LEGACY_KEY || key.startsWith(`${PREFIX}file.`)) continue;
      try {
        out[key] = JSON.parse(localStorage.getItem(key) ?? "null");
      } catch {
        /* not ours, or damaged: skip */
      }
    }
  } catch {
    /* storage unavailable */
  }
  return out;
}

function legacySets(): unknown[] | null {
  try {
    const parsed = JSON.parse(localStorageGet(LEGACY_SETS) ?? "null");
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

/** Move an API key an older version stored in localStorage into Windows Credential Manager. */
async function migrateApiKey() {
  const raw = localStorageGet(LEGACY_KEY);
  if (raw === null || !isTauri()) return;
  try {
    const key = JSON.parse(raw);
    if (typeof key === "string" && key.trim()) await invoke("api_key_save", { key });
    localStorage.removeItem(LEGACY_KEY);
  } catch {
    /* keep it for the next start rather than lose it */
  }
}

/** Load both files before the UI starts; on the first start, take over the old localStorage data. */
export async function initStorage(): Promise<void> {
  try {
    const [s, st] = await Promise.all([load("settings"), load("sets")]);
    settings = s && typeof s === "object" && !Array.isArray(s) ? (s as Record<string, unknown>) : {};
    sets = Array.isArray(st) ? st : null;
    if (s === null && st === null) {
      // First start with file storage. localStorage is left as it was, so an older version still works.
      settings = legacySettings();
      sets = legacySets();
      await Promise.all([write("settings", settings), sets ? write("sets", sets) : Promise.resolve()]);
    }
  } catch {
    saveFailed.value = true;
  }
  await migrateApiKey();
  window.addEventListener("beforeunload", flush);
}

function schedule(name: Name, value: () => unknown) {
  clearTimeout(timers[name]);
  timers[name] = setTimeout(() => {
    delete timers[name];
    write(name, value()).then(
      () => (saveFailed.value = false),
      () => (saveFailed.value = true),
    );
  }, SAVE_DELAY);
}

/** Write pending saves now (on close). */
export function flush() {
  if (timers.settings) {
    clearTimeout(timers.settings);
    delete timers.settings;
    void write("settings", settings).catch(() => {});
  }
  if (timers.sets) {
    clearTimeout(timers.sets);
    delete timers.sets;
    void write("sets", sets).catch(() => {});
  }
}

export function getSetting<T>(key: string, fallback: T): T {
  return key in settings ? (settings[key] as T) : fallback;
}

export function setSetting(key: string, value: unknown) {
  settings[key] = JSON.parse(JSON.stringify(value ?? null));
  schedule("settings", () => settings);
}

export function allSettings(): Record<string, unknown> {
  return { ...settings };
}

export function getSets(): unknown[] {
  return sets ?? [];
}

/** Schedule a save of the sets; `value` is serialised when the save runs, not on every edit. */
export function saveSets(value: unknown[]) {
  sets = value;
  schedule("sets", () => sets);
}
