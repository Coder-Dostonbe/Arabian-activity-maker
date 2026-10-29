import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";
import { getList, saveList } from "../storage";
import { newId } from "../util";

export type QuestionOutcome = "correct" | "wrong" | "skipped" | "unanswered";

export interface RunQuestion {
  shown: string;
  answer: string;
  ask: string;
  outcome: QuestionOutcome;
  rules: string[];
}

/** One finished test: when, which set, which class or group, the score and every question's outcome. */
export interface Run {
  id: string;
  date: number;
  setId: string;
  setName: string;
  group: string;
  correct: number;
  wrong: number;
  unanswered: number;
  total: number;
  questions: RunQuestion[];
}

export interface RuleStat {
  rule: string;
  asked: number;
  wrong: number;
}

const MAX_RUNS = 500;

// Test history, kept on this computer (results.json in the app data folder).
export const useResultsStore = defineStore("results", () => {
  const runs = ref<Run[]>(getList<Run>("results").filter((r) => r && typeof r === "object" && Array.isArray(r.questions)));

  watch(runs, (v) => saveList("results", v), { deep: true });

  function add(run: Omit<Run, "id">): Run {
    const saved = { ...run, id: newId() };
    runs.value = [saved, ...runs.value].slice(0, MAX_RUNS);
    return saved;
  }

  function remove(id: string) {
    runs.value = runs.value.filter((r) => r.id !== id);
  }

  const groups = computed(() => [...new Set(runs.value.map((r) => r.group).filter(Boolean))].sort());

  /** For each engine rule behind a question: how often it was asked and how often answered wrongly. */
  function ruleStats(selected: Run[]): RuleStat[] {
    const stats = new Map<string, RuleStat>();
    for (const run of selected) {
      for (const q of run.questions) {
        // The first rule is the one that decided the form; the others are routine (declension, spelling).
        const rule = q.rules[0];
        if (!rule) continue;
        const s = stats.get(rule) ?? { rule, asked: 0, wrong: 0 };
        s.asked++;
        if (q.outcome === "wrong") s.wrong++;
        stats.set(rule, s);
      }
    }
    return [...stats.values()].sort((a, b) => b.wrong / b.asked - a.wrong / a.asked || b.asked - a.asked);
  }

  return { runs, groups, add, remove, ruleStats };
});
