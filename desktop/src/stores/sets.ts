import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";
import { allSettings, getSets, saveFailed, saveSets, setSetting } from "../storage";
import { newId } from "../util";

export type Origin = "file" | "engine" | "claude" | "manual";
export type Form = "plural" | "dual";

export interface Item {
  id: string;
  prompt: string;
  answer: string;
  note: string;
  translation: string; // Uzbek meaning of `prompt`, for the Arabic ⇄ Uzbek exercises
  options: string[]; // wrong answers only
  approved: boolean;
  origin: Origin;
  uncertain?: boolean;
  form?: Form; // a plural / dual split off the word `base` it was written beside
  base?: string;
}

export interface WordSet {
  id: string;
  name: string;
  items: Item[];
  updated: number;
}

export type NewItem = Omit<Item, "id" | "approved" | "origin" | "translation"> & Partial<Pick<Item, "approved" | "translation">>;

const BACKUP_FORMAT = "arabmorph-backup";
const ORIGINS: Origin[] = ["file", "engine", "claude", "manual"];

const str = (v: unknown, max = 2000) => (typeof v === "string" ? v.slice(0, max) : "");

/** A set read from disk or a backup file, with every field checked; null if it is not a set. */
export function normalizeSet(raw: unknown): WordSet | null {
  const s = raw as Partial<WordSet> | null;
  if (!s || typeof s !== "object" || !Array.isArray(s.items)) return null;
  const items: Item[] = s.items.filter((i) => i && typeof i === "object").map((i) => ({
    id: str(i.id, 100) || newId(),
    prompt: str(i.prompt),
    answer: str(i.answer),
    note: str(i.note),
    translation: str(i.translation), // sets saved before 0.3.1 have none
    options: Array.isArray(i.options) ? i.options.map((o) => str(o)).filter(Boolean) : [],
    approved: i.approved === true,
    origin: ORIGINS.includes(i.origin as Origin) ? i.origin : "manual",
    ...(i.uncertain ? { uncertain: true } : {}),
    ...(i.form === "plural" || i.form === "dual" ? { form: i.form, base: str(i.base) } : {}),
  }));
  return { id: str(s.id, 100) || newId(), name: str(s.name, 200) || "—", items, updated: Number(s.updated) || Date.now() };
}

// The teacher's word sets, kept on this computer between runs.
export const useSetsStore = defineStore("sets", () => {
  const sets = ref<WordSet[]>(getSets().map(normalizeSet).filter((s): s is WordSet => s !== null));

  watch(sets, (v) => saveSets(v), { deep: true });

  const usable = computed(() => sets.value.filter((s) => s.items.some((i) => i.approved)));

  function get(id: string | null | undefined) {
    return sets.value.find((s) => s.id === id);
  }

  function makeItems(items: NewItem[], origin: Origin, approved: boolean): Item[] {
    return items.map((i) => ({ ...i, translation: i.translation ?? "", id: newId(), origin, approved: i.approved ?? approved }));
  }

  // Rows from a file the teacher chose are approved; generated rows must be reviewed first.
  function create(name: string, items: NewItem[] = [], origin: Origin = "manual"): WordSet {
    const set: WordSet = { id: newId(), name, items: makeItems(items, origin, origin === "file"), updated: Date.now() };
    sets.value.push(set);
    return set;
  }

  function append(id: string, items: NewItem[], origin: Origin) {
    const set = get(id);
    if (!set) return;
    set.items.push(...makeItems(items, origin, origin === "file" || origin === "manual"));
    set.updated = Date.now();
  }

  function remove(id: string) {
    sets.value = sets.value.filter((s) => s.id !== id);
  }

  /** Every set and setting in one JSON document, for "Export all". */
  function exportBackup(): string {
    return JSON.stringify({ format: BACKUP_FORMAT, version: 1, exported: new Date().toISOString(), sets: sets.value, settings: allSettings() }, null, 1);
  }

  /** Restore a backup: its sets replace those with the same id, others are added. Returns the count, or null if invalid. */
  function importBackup(text: string): number | null {
    let doc: { format?: unknown; sets?: unknown; settings?: unknown };
    try {
      doc = JSON.parse(text);
    } catch {
      return null;
    }
    if (doc?.format !== BACKUP_FORMAT || !Array.isArray(doc.sets)) return null;
    const restored = doc.sets.map(normalizeSet).filter((s): s is WordSet => s !== null);
    const ids = new Set(restored.map((s) => s.id));
    sets.value = [...sets.value.filter((s) => !ids.has(s.id)), ...restored];
    if (doc.settings && typeof doc.settings === "object" && !Array.isArray(doc.settings)) {
      for (const [key, value] of Object.entries(doc.settings)) {
        if (key.startsWith("arabmorph.") && key !== "arabmorph.claude.key") setSetting(key, value);
      }
    }
    return restored.length;
  }

  return { sets, usable, saveFailed, get, create, append, remove, exportBackup, importBackup };
});
