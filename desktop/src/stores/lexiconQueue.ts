import { defineStore } from "pinia";
import { ref, watch } from "vue";
import type { EntryProposal } from "../claude";
import { engine, type EntryDraft } from "../engine";
import { getList, saveList } from "../storage";
import { newId } from "../util";
import { useEngineStore } from "./engine";

/** A lexicon entry Claude proposed for a word the engine could not handle, waiting for the teacher's review. */
export interface Proposal {
  id: string;
  word: string;
  model: string;
  created: number;
  entry: EntryProposal;
}

export function toDraft(p: EntryProposal): EntryDraft {
  return {
    lemma: p.lemma,
    pos: p.pos,
    gender: p.gender,
    final_class: p.final_class,
    alif_origin: p.alif_origin || undefined,
    hamza_type: p.hamza_type || undefined,
    diptote: p.diptote,
    gloss_en: p.gloss_en,
    plurals: p.plurals.map((x) => ({ kind: x.kind, form: x.form || undefined, diptote: x.diptote })),
  };
}

// Proposals stay here (lexicon_queue.json) until approved into the user lexicon or rejected.
export const useLexiconQueue = defineStore("lexiconQueue", () => {
  const items = ref<Proposal[]>(getList<Proposal>("lexicon_queue").filter((p) => p && typeof p === "object" && p.entry));
  watch(items, (v) => saveList("lexicon_queue", v), { deep: true });

  function add(word: string, model: string, entry: EntryProposal): Proposal {
    const p = { id: newId(), word, model, created: Date.now(), entry };
    items.value = [p, ...items.value];
    return p;
  }

  function reject(id: string) {
    items.value = items.value.filter((p) => p.id !== id);
  }

  /** Store the (possibly edited) proposal in the user lexicon; the engine uses it from now on. */
  async function approve(id: string) {
    const p = items.value.find((x) => x.id === id);
    if (!p) return null;
    const r = await engine.addEntry(toDraft(p.entry));
    reject(id);
    useEngineStore().lexicon = null; // reload the lexicon page with the new entry
    void useEngineStore().connect(); // entry count in the footer
    return r;
  }

  return { items, add, reject, approve };
});
