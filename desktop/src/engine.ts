// Typed bridge to the local engine service (via the Rust `engine_call` command).
import { invoke, isTauri } from "@tauri-apps/api/core";

export type CaseName = "nominative" | "accusative" | "genitive";
export type NumberName = "singular" | "dual" | "plural";
export type PluralKind = "sound_masculine" | "sound_feminine" | "broken";
export type StateName = "indefinite" | "definite" | "construct";

export interface Rule {
  id: string;
  name_ar: string;
  explanation_ar: string;
  explanation_en: string;
  example: string;
  reference: string;
  confidence: number;
  review_status: string;
}

export interface LexiconEntry {
  id: string;
  lemma: string;
  pos: string;
  gender: string;
  final_class: string;
  alif_origin: string | null;
  hamza_type: string | null;
  diptote: boolean;
  gloss_en: string;
  verified: boolean;
  source: string;
  plurals: { kind: PluralKind; form: string | null; diptote: boolean }[];
}

export interface EngineVersion {
  engine: string;
  rules: number;
  lexicon_entries: number;
  lexicon_sources: string[];
}

/** One row read from a teacher's file. `options` are wrong answers only. */
export interface RawItem {
  prompt: string;
  answer: string;
  note: string;
  options: string[];
}

export interface ImportResult {
  sets: { name: string; items: RawItem[] }[];
  warnings: string[];
}

export interface BuiltItem {
  prompt: string;
  answer: string;
  options: string[];
  uncertain: boolean;
  warnings: string[];
}

export interface BuildResult {
  items: BuiltItem[];
  skipped: { word: string; reason: "error" | "ambiguous"; detail: string }[];
}

export interface BuildParams {
  words: string[];
  number: NumberName;
  case: CaseName;
  state: StateName;
}

interface Reply<T> {
  id: number | null;
  ok: boolean;
  result?: T;
  error?: string;
  code?: string;
}

let nextId = 1;

export class EngineError extends Error {
  constructor(message: string, public code = "bad_request") {
    super(message);
  }
}

async function call<T>(op: string, params: object = {}): Promise<T> {
  if (!isTauri()) throw new EngineError("desktop only", "desktop_only");
  const reply = await invoke<Reply<T>>("engine_call", { request: { id: nextId++, op, params } });
  if (!reply.ok) throw new EngineError(reply.error ?? "", reply.code);
  return reply.result as T;
}

export const engine = {
  version: () => call<EngineVersion>("version"),
  rules: () => call<Rule[]>("rules"),
  lexicon: () => call<LexiconEntry[]>("lexicon"),
  importFile: (name: string, data: string) => call<ImportResult>("import_file", { name, data }),
  buildItems: (p: BuildParams) => call<BuildResult>("build_items", p),
};
