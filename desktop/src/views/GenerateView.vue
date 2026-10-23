<script setup lang="ts">
import { computed, ref } from "vue";
import { engine, type CaseName, type GenerationResult, type NumberName, type Paradigm, type PluralKind } from "../engine";
import { caseLabel, kindLabel, numberLabel } from "../labels";
import { useEngineStore } from "../stores/engine";
import FormCard from "../components/FormCard.vue";
import ParadigmTable from "../components/ParadigmTable.vue";
import ResultNotes from "../components/ResultNotes.vue";

type CaseChoice = CaseName | "all";
type StateChoice = "input" | "indefinite" | "definite" | "construct";

const store = useEngineStore();
const word = ref("");
const number = ref<NumberName>("dual");
const caseChoice = ref<CaseChoice>("all");
const stateChoice = ref<StateChoice>("input");
const kind = ref<PluralKind | "">("");
const after = ref("");

const loading = ref(false);
const failure = ref<string | null>(null);
const single = ref<GenerationResult | null>(null);
const table = ref<Paradigm | null>(null);
const selectedKey = ref<string | null>(null);
const selected = ref<GenerationResult | null>(null);

const usesContext = computed(() => after.value.trim() !== "");
const showTable = computed(() => caseChoice.value === "all" && !usesContext.value);

const examples: Record<NumberName, string[]> = {
  singular: ["أحمد", "كتاب", "قاضٍ", "صحراء"],
  dual: ["كتاب", "شجرة", "عصا", "مستشفى", "سماء"],
  plural: ["مدرسة", "مهندس", "ليلة", "صلاة", "منشأة"],
};

async function run() {
  const w = word.value.trim();
  if (!w) return;
  loading.value = true;
  failure.value = null;
  single.value = table.value = selected.value = null;
  selectedKey.value = null;
  const k = number.value === "plural" && kind.value ? kind.value : null;
  try {
    await store.loadRules();
    if (showTable.value) {
      table.value = await engine.paradigm({ word: w, number: number.value, kind: k });
    } else {
      single.value = await engine.generate({
        word: w,
        number: number.value,
        case: caseChoice.value === "all" ? "nominative" : caseChoice.value,
        definite: stateChoice.value === "definite" ? true : stateChoice.value === "input" ? null : false,
        construct: stateChoice.value === "construct",
        kind: k,
        after: usesContext.value ? after.value.trim() : null,
      });
    }
  } catch (e) {
    failure.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}

function pick(key: string, result: GenerationResult) {
  selectedKey.value = key;
  selected.value = result;
}

function useExample(w: string) {
  word.value = w;
  run();
}
</script>

<template>
  <section>
    <h1>Shakl yasash</h1>
    <p class="muted">Birlikdagi arabcha otni kiriting: diakritika bilan, qisman yoki umuman diakritikasiz.</p>

    <form class="panel controls" @submit.prevent="run">
      <label class="word-field">
        <span class="small muted">So'z</span>
        <input v-model="word" type="text" class="ar word" lang="ar" dir="rtl" maxlength="64"
               placeholder="مثلاً: كتاب" autofocus aria-label="Arabcha so'z" />
      </label>

      <fieldset>
        <legend class="small muted">Son</legend>
        <div class="seg">
          <label v-for="(label, n) in numberLabel" :key="n" :class="{ on: number === n }">
            <input v-model="number" type="radio" :value="n" /> {{ label }}
          </label>
        </div>
      </fieldset>

      <div class="row">
        <label>
          <span class="small muted">Kelishik</span>
          <select v-model="caseChoice" :disabled="usesContext">
            <option value="all">Hammasi (jadval)</option>
            <option v-for="(label, c) in caseLabel" :key="c" :value="c">{{ label }}</option>
          </select>
        </label>
        <label>
          <span class="small muted">Holat</span>
          <select v-model="stateChoice" :disabled="showTable">
            <option value="input">Kiritilganidek</option>
            <option value="indefinite">Noaniq (نكرة)</option>
            <option value="definite">Aniq — ال</option>
            <option value="construct">Izofa (مضاف)</option>
          </select>
        </label>
        <label v-if="number === 'plural'">
          <span class="small muted">Ko'plik turi</span>
          <select v-model="kind">
            <option value="">Lug'atdagi barcha turlar</option>
            <option v-for="(label, k) in kindLabel" :key="k" :value="k">{{ label }}</option>
          </select>
        </label>
        <label>
          <span class="small muted">Oldingi so'z (ixtiyoriy)</span>
          <input v-model="after" type="text" class="ar ctx" lang="ar" dir="rtl" maxlength="64" placeholder="في، إنّ، كان…" />
        </label>
      </div>
      <p v-if="usesContext" class="small muted">Kelishik oldingi so'zdan aniqlanadi (حرف جر، إنّ وأخواتها، كان وأخواتها).</p>
      <p v-if="number === 'plural' && kind && kind !== 'broken'" class="small muted">
        Lug'atda yo'q so'z uchun bu tur siz tomondan tasdiqlangan deb hisoblanadi va ishonch darajasi pasaytiriladi.
      </p>

      <div class="actions">
        <button class="primary" type="submit" :disabled="loading || !word.trim() || !!store.error">
          {{ loading ? "Yasalmoqda…" : "Yasash" }}
        </button>
        <span class="small muted">Misollar:</span>
        <button v-for="ex in examples[number]" :key="ex" type="button" class="ex ar" lang="ar" @click="useExample(ex)">{{ ex }}</button>
      </div>
    </form>

    <div v-if="failure" class="notice err">{{ failure }}</div>

    <template v-if="table">
      <h2>Jadval</h2>
      <ParadigmTable :paradigm="table" :selected="selectedKey" @select="pick" />
      <p v-if="!selected" class="small muted hint">Tafsilotlarni ko'rish uchun katakni bosing.</p>
      <div v-if="selected" class="details">
        <ResultNotes :result="selected" />
        <div class="cards"><FormCard v-for="(f, i) in selected.forms" :key="i" :form="f" /></div>
      </div>
    </template>

    <template v-if="single">
      <ResultNotes :result="single" />
      <div class="cards"><FormCard v-for="(f, i) in single.forms" :key="i" :form="f" /></div>
    </template>
  </section>
</template>

<style scoped>
.controls { display: flex; flex-direction: column; gap: 14px; margin: 16px 0 20px; }
.word-field { display: flex; flex-direction: column; gap: 4px; }
.word { font-size: 30px; padding: 6px 12px; }
.ctx { font-size: 20px; padding: 2px 10px; }
fieldset { border: 0; padding: 0; margin: 0; }
legend { margin-bottom: 4px; }
.seg { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.seg label { padding: 6px 14px; cursor: pointer; border-inline-end: 1px solid var(--border); }
.seg label:last-child { border-inline-end: 0; }
.seg label.on { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.seg input { position: absolute; opacity: 0; pointer-events: none; }
.seg label:focus-within { outline: 2px solid var(--accent); outline-offset: -2px; }
.row { display: flex; flex-wrap: wrap; gap: 14px; }
.row label { display: flex; flex-direction: column; gap: 4px; min-width: 170px; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.ex { font-size: 18px; padding: 0 10px; }
.cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); }
.details { margin-top: 16px; }
.hint { margin-top: 8px; }
</style>
