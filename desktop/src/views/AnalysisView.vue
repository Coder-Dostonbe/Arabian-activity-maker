<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { isTauri } from "@tauri-apps/api/core";
import RuleHint from "../components/RuleHint.vue";
import { ClaudeError, proposeEntry, savedKey, useModel, MODELS } from "../claude";
import {
  engine,
  type AnalysisResult,
  type CaseName,
  type Form,
  type GenerationResult,
  type NumberName,
  type Paradigm,
  type StateName,
} from "../engine";
import { useI18n } from "../i18n";
import { useLexiconQueue } from "../stores/lexiconQueue";
import { persisted } from "../util";

// "Tahlil": every form of a word (3 cases × 3 states for each number), with the reason behind each,
// and the reverse analysis of the word as typed.
const m = useI18n();
const queue = useLexiconQueue();

const NUMBERS: NumberName[] = ["singular", "dual", "plural"];
const STATES: StateName[] = ["indefinite", "definite", "construct"];
const CASES: CaseName[] = ["nominative", "accusative", "genitive"];

const word = persisted("arabmorph.analysis.word", "");
const busy = ref(false);
const failure = ref<string | null>(null);
const tables = ref<Partial<Record<NumberName, Paradigm>>>({});
const analysis = ref<AnalysisResult | null>(null);
const selected = ref<{ number: NumberName; state: StateName; case: CaseName } | null>(null);

const cell = (n: NumberName, s: StateName, c: CaseName): GenerationResult | undefined => tables.value[n]?.[s]?.[c];
const selectedResult = computed(() => (selected.value ? cell(selected.value.number, selected.value.state, selected.value.case) : undefined));
const suggestions = computed(() => [
  ...new Set([...(analysis.value?.suggestions ?? []), ...NUMBERS.flatMap((n) => cell(n, "indefinite", "nominative")?.suggestions ?? [])]),
]);
// Offer Claude only for a word the lexicon does not know.
const unknown = computed(() => !!analysis.value && !analysis.value.analyses.some((a) => a.in_lexicon));

async function run(w?: string) {
  if (w !== undefined) word.value = w;
  const text = word.value.trim();
  if (!text) return;
  busy.value = true;
  failure.value = null;
  selected.value = null;
  proposal.value = null;
  try {
    const [a, ...rows] = await Promise.all([engine.analyze(text), ...NUMBERS.map((n) => engine.paradigm(text, n))]);
    analysis.value = a;
    tables.value = Object.fromEntries(NUMBERS.map((n, i) => [n, rows[i]]));
  } catch (e) {
    failure.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

function confidenceClass(f: Form) {
  return f.confidence >= 0.85 ? "ok" : f.confidence >= 0.6 ? "warn" : "err";
}

// --- Ask Claude for a lexicon entry -----------------------------------------------
const model = useModel();
const hasKey = ref(false);
const asking = ref(false);
const proposal = ref<string | null>(null);

onMounted(async () => {
  if (word.value) void run();
  if (!isTauri()) return;
  try {
    hasKey.value = await savedKey.exists();
  } catch {
    /* no Credential Manager */
  }
});

async function askClaude() {
  const text = word.value.trim();
  if (!text) return;
  asking.value = true;
  proposal.value = null;
  try {
    const entry = await proposeEntry(null, true, text, model.value);
    queue.add(text, model.value, entry);
    proposal.value = m.value.analysis.queued(entry.lemma);
  } catch (e) {
    const kind = e instanceof ClaudeError ? e.kind : "other";
    proposal.value = m.value.gen.claudeErrors[kind] ?? (e as Error).message;
  } finally {
    asking.value = false;
  }
}
</script>

<template>
  <section>
    <h1>{{ m.analysis.title }}</h1>
    <p class="muted intro">{{ m.analysis.intro }}</p>
    <form class="search" @submit.prevent="run()">
      <input v-model="word" type="text" class="ar word" lang="ar" dir="rtl" :placeholder="m.analysis.placeholder" />
      <button class="primary" type="submit" :disabled="busy || !word.trim()">{{ busy ? m.gen.generating : m.analysis.run }}</button>
    </form>
    <div v-if="failure" class="notice err">{{ failure }}</div>

    <div v-if="suggestions.length" class="notice warn">
      {{ m.analysis.didYouMean }}
      <button v-for="s in suggestions" :key="s" class="small-btn ar" @click="run(s)">{{ s }}</button>
    </div>

    <div v-if="analysis" class="panel">
      <h2>{{ m.analysis.reverse }}</h2>
      <p v-if="!analysis.analyses.length" class="muted">{{ analysis.errors[0] ?? m.analysis.noAnalysis }}</p>
      <table v-else>
        <thead>
          <tr><th>{{ m.analysis.singular }}</th><th>{{ m.analysis.number }}</th><th>{{ m.analysis.state }}</th><th>{{ m.analysis.case }}</th><th /></tr>
        </thead>
        <tbody>
          <tr v-for="(a, i) in analysis.analyses" :key="i">
            <td class="ar cell-big"><button class="link ar" @click="run(a.singular)">{{ a.singular }}</button></td>
            <td>{{ m.grammar.number[a.number] }}<span v-if="a.kind" class="small muted"> · {{ m.grammar.kind[a.kind] }}</span></td>
            <td>{{ m.grammar.state[a.state] }}</td>
            <td>{{ a.cases.map((c) => m.grammar.case[c]).join(", ") }}</td>
            <td><span v-if="!a.in_lexicon" class="badge warn">{{ m.analysis.notInLexicon }}</span></td>
          </tr>
        </tbody>
      </table>
      <p v-if="analysis.status === 'ambiguous'" class="small muted">{{ m.analysis.ambiguous }}</p>
    </div>

    <div v-if="unknown" class="panel ask">
      <h2>{{ m.analysis.askTitle }}</h2>
      <p class="small muted">{{ m.analysis.askIntro }}</p>
      <p v-if="!hasKey" class="small muted">{{ m.analysis.needKey }}</p>
      <div v-else class="row">
        <select v-model="model">
          <option v-for="mo in MODELS" :key="mo.id" :value="mo.id">{{ m.models.names[mo.id] }}</option>
        </select>
        <button :disabled="asking" @click="askClaude">{{ asking ? m.gen.generating : m.analysis.ask }}</button>
      </div>
      <p v-if="proposal" class="notice">{{ proposal }} <RouterLink to="/lexicon">{{ m.nav.lexicon }}</RouterLink></p>
    </div>

    <div v-for="n in NUMBERS" :key="n" class="panel">
      <h2>{{ m.grammar.number[n] }}</h2>
      <table v-if="tables[n]" class="grid">
        <thead>
          <tr><th /><th v-for="c in CASES" :key="c">{{ m.grammar.case[c] }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="s in STATES" :key="s">
            <th>{{ m.grammar.state[s] }}</th>
            <td v-for="c in CASES" :key="c" class="cell" :class="{ on: selected?.number === n && selected?.state === s && selected?.case === c }"
                @click="selected = { number: n, state: s, case: c }">
              <template v-if="cell(n, s, c)?.forms.length">
                <div v-for="(f, i) in cell(n, s, c)!.forms" :key="i" class="ar form">{{ f.vocalized }}</div>
                <span v-if="cell(n, s, c)!.status === 'ambiguous'" class="badge warn small">{{ m.analysis.ambiguousShort }}</span>
              </template>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="selected?.number === n && selectedResult" class="details">
        <p v-for="e in selectedResult.errors" :key="e" class="notice err">{{ e }}</p>
        <div v-for="(f, i) in selectedResult.forms" :key="i" class="form-detail">
          <div class="ar big">{{ f.vocalized }}</div>
          <div class="small">
            <span class="badge">{{ m.analysis.sources[f.source] }}</span>
            <span class="badge" :class="confidenceClass(f)">{{ m.analysis.confidence(Math.round(f.confidence * 100)) }}</span>
            <span v-if="f.kind" class="badge">{{ m.grammar.kind[f.kind] }}</span>
          </div>
          <p v-if="f.condition" class="small">{{ m.analysis.condition }}: {{ f.condition }}</p>
          <ul v-if="f.warnings.length" class="small muted">
            <li v-for="w in f.warnings" :key="w">{{ w }}</li>
          </ul>
          <RuleHint :ids="f.rules" :limit="6" />
        </div>
        <ul v-if="selectedResult.warnings.length" class="small muted">
          <li v-for="w in selectedResult.warnings" :key="w">{{ w }}</li>
        </ul>
      </div>
      <p v-else-if="tables[n]" class="small muted">{{ m.analysis.clickCell }}</p>
    </div>
  </section>
</template>

<style scoped>
.intro { max-width: 760px; }
.search { display: flex; gap: 8px; margin: 12px 0; max-width: 560px; }
.search .word { flex: 1; font-size: 26px; }
.panel { margin-top: 12px; overflow-x: auto; }
.grid th { text-align: start; white-space: nowrap; }
.cell { cursor: pointer; vertical-align: top; border-radius: 6px; }
.cell:hover { background: var(--surface-2); }
.cell.on { background: var(--accent-soft); }
.form { font-size: 24px; line-height: 1.5; }
.cell-big { font-size: 22px; }
.details { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; }
.form-detail { display: flex; flex-direction: column; gap: 6px; border-top: 1px solid var(--border); padding-top: 10px; }
.big { font-size: 32px; }
.badge + .badge { margin-inline-start: 4px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.small-btn { font-size: 16px; padding: 2px 10px; margin-inline-start: 6px; }
.link { background: none; border: 0; padding: 0; color: var(--accent); cursor: pointer; font-size: inherit; }
</style>
