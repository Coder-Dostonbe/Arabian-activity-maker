// Optional online assistant: drafts activity items with Claude using the teacher's own API key.
// Nothing here runs unless the teacher asks for it; the offline engine needs no network.
// The request is made by the Rust shell (src-tauri/src/claude.rs), which also keeps the key in
// Windows Credential Manager: the key is never stored by, or sent back to, the webview.
import { invoke } from "@tauri-apps/api/core";

export const MAX_DRAFT_ITEMS = 40;

export interface DraftItem {
  prompt: string;
  answer: string;
  note: string;
  options: string[];
}

export type ClaudeErrorKind = "auth" | "rate" | "network" | "refusal" | "invalid" | "other";

export class ClaudeError extends Error {
  constructor(public kind: ClaudeErrorKind, message = "") {
    super(message);
  }
}

function clean(value: unknown, max = 300): string {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim().slice(0, max) : "";
}

/** Whether a key is saved in Credential Manager. */
export const savedKey = {
  exists: () => invoke<boolean>("api_key_status"),
  forget: () => invoke<void>("api_key_forget"),
};

/** `key` null uses the saved key; `remember` saves a typed key, unchecking it removes the saved one. */
export async function draftItems(key: string | null, remember: boolean, topic: string, count: number, language: string): Promise<DraftItem[]> {
  let raw: unknown;
  try {
    raw = await invoke<unknown>("claude_draft", { key, remember, topic, count, language });
  } catch (e) {
    const f = e as { kind?: unknown; message?: unknown } | null;
    if (f && typeof f.kind === "string") throw new ClaudeError(f.kind as ClaudeErrorKind, typeof f.message === "string" ? f.message : "");
    throw new ClaudeError("other", String(e));
  }
  if (!Array.isArray(raw)) throw new ClaudeError("invalid");

  const items: DraftItem[] = [];
  for (const r of raw.slice(0, MAX_DRAFT_ITEMS)) {
    const prompt = clean(r?.prompt);
    const answer = clean(r?.answer);
    if (!prompt || !answer) continue;
    const options = Array.isArray(r?.options)
      ? [...new Set(r.options.map((o: unknown) => clean(o)))].filter((o): o is string => !!o && o !== answer).slice(0, 6)
      : [];
    items.push({ prompt, answer, note: clean(r?.note), options });
  }
  if (!items.length) throw new ClaudeError("invalid");
  return items;
}
