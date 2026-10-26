import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";
import { newId, readStorage, writeStorage } from "../util";

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

const KEY = "arabmorph.sets.v1";

// The teacher's word sets, kept on this computer between runs.
export const useSetsStore = defineStore("sets", () => {
  // Sets saved before 0.3.1 have no `translation`.
  const sets = ref<WordSet[]>(
    readStorage<WordSet[]>(KEY, []).map((s) => ({ ...s, items: s.items.map((i) => ({ ...i, translation: i.translation ?? "" })) })),
  );
  const saveFailed = ref(false);

  watch(sets, (v) => (saveFailed.value = !writeStorage(KEY, v)), { deep: true });

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

  return { sets, usable, saveFailed, get, create, append, remove };
});
