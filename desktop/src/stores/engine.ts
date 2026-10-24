import { defineStore } from "pinia";
import { ref } from "vue";
import { engine, EngineError, type EngineVersion, type LexiconEntry, type Rule } from "../engine";

// Engine status plus data that never changes while the app runs (rules, lexicon).
export const useEngineStore = defineStore("engine", () => {
  const version = ref<EngineVersion | null>(null);
  const error = ref<string | null>(null);
  const errorCode = ref<string | null>(null);
  const rules = ref<Rule[] | null>(null);
  const lexicon = ref<LexiconEntry[] | null>(null);

  async function connect() {
    try {
      version.value = await engine.version();
      error.value = errorCode.value = null;
    } catch (e) {
      error.value = (e as Error).message;
      errorCode.value = e instanceof EngineError ? e.code : null;
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

  return { version, error, errorCode, rules, lexicon, connect, loadRules, loadLexicon };
});
