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

/** One item read from a teacher's file. `options` are wrong answers only. */
export interface RawItem {
  prompt: string;
  answer: string;
  note: string;
  translation: string;
  options: string[];
  /** Set on a plural / dual the service split off the word `base` it was written beside. */
  form?: "plural" | "dual";
  base?: string;
  /** A translation or form the service guessed; the teacher should check it. */
  uncertain?: boolean;
}

export interface ImportResult {
  sets: { name: string; items: RawItem[] }[];
  warnings: string[];
}

export interface BuiltItem {
  prompt: string;
  answer: string;
  options: string[];
  rules: string[];
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

export interface Form {
  text: string;
  vocalized: string;
  number: NumberName;
  case: CaseName;
  definite: boolean;
  construct: boolean;
  rules: string[];
  source: "rule" | "lexicon" | "heuristic" | "asserted";
  confidence: number;
  condition: string | null;
  warnings: string[];
  kind: PluralKind | null;
  diptote: boolean | null;
}

export interface GenerationResult {
  input: string;
  status: "ok" | "ambiguous" | "error";
  forms: Form[];
  warnings: string[];
  errors: string[];
  assumptions: string[];
  suggestions: string[];
}

/** state → case → result, as returned by the `paradigm` op. */
export type Paradigm = Record<StateName, Record<CaseName, GenerationResult>>;

export interface Analysis {
  singular: string;
  number: NumberName;
  state: StateName;
  cases: CaseName[];
  kind: PluralKind | null;
  vocalized: string;
  entry_id: string | null;
  in_lexicon: boolean;
  rules: string[];
  source: string;
  confidence: number;
  condition: string | null;
}

export interface AnalysisResult {
  input: string;
  status: "ok" | "ambiguous" | "error";
  analyses: Analysis[];
  warnings: string[];
  errors: string[];
  suggestions: string[];
}

export type CheckStatus = "engine_agrees" | "engine_disagrees" | "not_checkable";

export interface Check {
  status: CheckStatus;
  engine: string[];
  detail: string;
}

/** A lexicon entry as proposed (by Claude) or stored in the teacher's own lexicon. */
export interface EntryDraft {
  lemma: string;
  pos: string;
  gender: string;
  final_class: string;
  alif_origin?: string;
  hamza_type?: string;
  diptote?: boolean;
  gloss_en?: string;
  plurals?: { kind: PluralKind; form?: string; diptote?: boolean }[];
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
  paradigm: (word: string, number: NumberName) => call<Paradigm>("paradigm", { word, number }),
  analyze: (word: string) => call<AnalysisResult>("analyze", { word }),
  verifyItems: (items: { prompt: string; answer: string }[]) => call<Check[]>("verify_items", { items }),
  userLexicon: () => call<{ entries: (EntryDraft & { id: string })[]; configured: boolean }>("user_lexicon"),
  checkEntry: (entry: EntryDraft) => call<{ entry: EntryDraft; problems: string[] }>("user_lexicon_check", { entry }),
  addEntry: (entry: EntryDraft) => call<{ entry: EntryDraft & { id: string }; homographs: number }>("user_lexicon_add", { entry }),
  removeEntry: (id: string) => call<{ removed: boolean }>("user_lexicon_remove", { id }),
  exportXlsx: (sheets: Record<string, string[][]>) => call<{ data: string }>("export_xlsx", { sheets }),
};
