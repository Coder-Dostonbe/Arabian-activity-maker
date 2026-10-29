// Optional online assistant: drafts activity items with Claude using the teacher's own API key.
// Nothing here runs unless the teacher asks for it; the offline engine needs no network.
// The request is made by the Rust shell (src-tauri/src/claude.rs), which also keeps the key in
// Windows Credential Manager: the key is never stored by, or sent back to, the webview.
import { invoke } from "@tauri-apps/api/core";
import { persisted } from "./util";

export const MAX_DRAFT_ITEMS = 40;

/** Cheapest first: it is the default. Prices per million tokens (input / output), Claude API, 2026-10. */
export const MODELS = [
  { id: "claude-haiku-5-5", input: 0.1, output: 0.5 },
  { id: "claude-sonnet-5-5", input: 2, output: 10 },
  { id: "claude-opus-5-5", input: 4, output: 20 },
] as const;
export type ModelId = (typeof MODELS)[number]["id"];

/** The teacher's model choice, remembered; an unknown saved value falls back to the cheapest. */
export function useModel() {
  const model = persisted<ModelId>("arabmorph.claude.model", MODELS[0].id);
  if (!MODELS.some((m) => m.id === model.value)) model.value = MODELS[0].id;
  return model;
}

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
async function claude<T>(command: string, args: Record<string, unknown>): Promise<T> {
  try {
    return await invoke<T>(command, args);
  } catch (e) {
    const f = e as { kind?: unknown; message?: unknown } | null;
    if (f && typeof f.kind === "string") throw new ClaudeError(f.kind as ClaudeErrorKind, typeof f.message === "string" ? f.message : "");
    throw new ClaudeError("other", String(e));
  }
}

/** Claude's description of a word for the lexicon; it goes to the review queue, never straight into the lexicon. */
export function proposeEntry(key: string | null, remember: boolean, word: string, modelId: ModelId) {
  return claude<EntryProposal>("claude_lexicon", { key, remember, word, modelId });
}

export interface EntryProposal {
  lemma: string;
  pos: string;
  gender: string;
  final_class: string;
  alif_origin: string;
  hamza_type: string;
  diptote: boolean;
  gloss_en: string;
  plurals: { kind: "sound_masculine" | "sound_feminine" | "broken"; form: string; diptote: boolean }[];
  note: string;
}

export async function draftItems(key: string | null, remember: boolean, topic: string, count: number, language: string,
                                 modelId: ModelId): Promise<DraftItem[]> {
  const raw = await claude<unknown>("claude_draft", { key, remember, topic, count, language, modelId });
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
