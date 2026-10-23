<script setup lang="ts">
import { ref } from "vue";
import type { GeneratedForm } from "../engine";
import { caseLabel, kindLabel, sourceHint, sourceLabel } from "../labels";
import { useEngineStore } from "../stores/engine";

const props = defineProps<{ form: GeneratedForm }>();
const store = useEngineStore();
const copied = ref(false);
const showRules = ref(false);

function confidenceClass(c: number) {
  return c >= 0.85 ? "ok" : c >= 0.6 ? "accent" : "warn";
}

async function copy() {
  await navigator.clipboard.writeText(props.form.vocalized);
  copied.value = true;
  setTimeout(() => (copied.value = false), 1200);
}
</script>

<template>
  <article class="card panel">
    <div class="top">
      <div class="forms">
        <div class="vocalized ar" lang="ar">{{ form.vocalized }}</div>
        <div class="plain ar muted" lang="ar">{{ form.text }}</div>
      </div>
      <button class="copy" :aria-label="`${form.vocalized} nusxasini olish`" @click="copy">
        {{ copied ? "Nusxalandi" : "Nusxa olish" }}
      </button>
    </div>

    <div class="badges">
      <span class="badge">{{ caseLabel[form.case] }}</span>
      <span v-if="form.definite" class="badge">ال bilan</span>
      <span v-if="form.construct" class="badge">Izofa</span>
      <span v-if="form.kind" class="badge">{{ kindLabel[form.kind] }}</span>
      <span v-if="form.diptote" class="badge">Mamnu' min as-sarf</span>
      <span class="badge" :title="sourceHint[form.source]">Manba: {{ sourceLabel[form.source] ?? form.source }}</span>
      <span class="badge" :class="confidenceClass(form.confidence)" title="Qo'lda belgilangan ishonch darajasi (ehtimollik emas)">
        Ishonch {{ Math.round(form.confidence * 100) }}%
      </span>
    </div>

    <p v-if="form.condition" class="condition">Shart: {{ form.condition }}</p>

    <ul v-if="form.warnings.length" class="plain warnings">
      <li v-for="w in form.warnings" :key="w" class="notice warn small">{{ w }}</li>
    </ul>

    <button class="link small" @click="showRules = !showRules">
      {{ showRules ? "Qoidalarni yashirish" : `Qo'llangan qoidalar (${form.rules.length})` }}
    </button>
    <ul v-if="showRules" class="plain rules">
      <li v-for="id in form.rules" :key="id">
        <template v-if="store.ruleById(id)">
          <div class="rule-name ar" lang="ar">{{ store.ruleById(id)!.name_ar }}</div>
          <div class="ar small" lang="ar">{{ store.ruleById(id)!.explanation_ar }}</div>
          <div class="small muted">{{ store.ruleById(id)!.explanation_en }}</div>
        </template>
        <code class="small muted">{{ id }}</code>
      </li>
    </ul>
  </article>
</template>

<style scoped>
.card { display: flex; flex-direction: column; gap: 10px; }
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.forms { flex: 1; text-align: end; }
.vocalized { font-size: 38px; line-height: 1.5; }
.plain { font-size: 20px; }
.copy { font-size: 12px; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; }
.condition { margin: 0; color: var(--warn); }
.warnings li { margin-bottom: 4px; }
.link { align-self: flex-start; border: 0; padding: 0; background: none; color: var(--accent); }
.link:hover { background: none; text-decoration: underline; }
.rules li { padding: 8px 0; border-top: 1px solid var(--border); }
.rule-name { font-size: 18px; font-weight: 600; }
</style>
