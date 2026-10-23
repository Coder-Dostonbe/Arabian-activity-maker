// Typed bridge to the local engine service (via the Rust `engine_call` command).
import { invoke, isTauri } from "@tauri-apps/api/core";

export type CaseName = "nominative" | "accusative" | "genitive";
export type NumberName = "singular" | "dual" | "plural";
export type PluralKind = "sound_masculine" | "sound_feminine" | "broken";
export type Status = "ok" | "ambiguous" | "error";
export type StateName = "indefinite" | "definite" | "construct";

export interface GeneratedForm {
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
  status: Status;
  forms: GeneratedForm[];
  warnings: string[];
  errors: string[];
  assumptions: string[];
}

export type Paradigm = Record<StateName, Record<CaseName, GenerationResult>>;

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

export interface GenerateParams {
  word: string;
  number: NumberName;
  case?: CaseName;
  definite?: boolean | null;
  construct?: boolean;
  kind?: PluralKind | null;
  after?: string | null;
}

interface Reply<T> {
  id: number | null;
  ok: boolean;
  result?: T;
  error?: string;
}

let nextId = 1;

export class EngineError extends Error {}

async function call<T>(op: string, params: object = {}): Promise<T> {
  if (!isTauri()) {
    throw new EngineError("Dvigatel faqat ArabMorph AI desktop ilovasi ichida ishlaydi.");
  }
  const reply = await invoke<Reply<T>>("engine_call", { request: { id: nextId++, op, params } });
  if (!reply.ok) throw new EngineError(reply.error ?? "Noma'lum xato");
  return reply.result as T;
}

export const engine = {
  version: () => call<EngineVersion>("version"),
  generate: (p: GenerateParams) => call<GenerationResult>("generate", p),
  paradigm: (p: Pick<GenerateParams, "word" | "number" | "kind">) => call<Paradigm>("paradigm", p),
  rules: () => call<Rule[]>("rules"),
  lexicon: () => call<LexiconEntry[]>("lexicon"),
};
