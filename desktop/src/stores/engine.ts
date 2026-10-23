import { defineStore } from "pinia";
import { ref } from "vue";
import { engine, type EngineVersion, type LexiconEntry, type Rule } from "../engine";

// Engine status plus data that never changes while the app runs (rules, lexicon).
export const useEngineStore = defineStore("engine", () => {
  const version = ref<EngineVersion | null>(null);
  const error = ref<string | null>(null);
  const rules = ref<Rule[] | null>(null);
  const lexicon = ref<LexiconEntry[] | null>(null);

  async function connect() {
    try {
      version.value = await engine.version();
      error.value = null;
    } catch (e) {
      error.value = (e as Error).message;
    }
  }

  async function loadRules() {
    rules.value ??= await engine.rules();
    return rules.value;
  }

  async function loadLexicon() {
    lexicon.value ??= await engine.lexicon();
    return lexicon.value;
  }

  function ruleById(id: string): Rule | undefined {
    return rules.value?.find((r) => r.id === id);
  }

  return { version, error, rules, lexicon, connect, loadRules, loadLexicon, ruleById };
});
