<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { LexiconEntry } from "../engine";
import { useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";

const store = useEngineStore();
const m = useI18n();
const entries = ref<LexiconEntry[]>([]);
const query = ref("");
const failure = ref<string | null>(null);

// Matching ignores vocalisation marks and tatweel, but keeps hamza seats.
const strip = (s: string) => s.normalize("NFC").replace(/[ً-ْٰـ]/g, "");

const filtered = computed(() => {
  const q = strip(query.value.trim()).toLowerCase();
  if (!q) return entries.value;
  return entries.value.filter((e) => strip(e.lemma).includes(q) || e.gloss_en.toLowerCase().includes(q));
});

onMounted(async () => {
  try {
    entries.value = await store.loadLexicon();
  } catch (e) {
    failure.value = (e as Error).message;
  }
});
</script>

<template>
  <section>
    <h1>{{ m.lexicon.title }}</h1>
    <p class="muted">{{ m.lexicon.intro }}</p>
    <input v-model="query" type="search" class="search" :placeholder="m.lexicon.search" :aria-label="m.lexicon.search" />
    <div v-if="failure" class="notice err">{{ failure }}</div>
    <table v-else class="panel lex">
      <thead>
        <tr>
          <th>{{ m.lexicon.cols.word }}</th><th>{{ m.lexicon.cols.meaning }}</th><th>{{ m.lexicon.cols.pos }}</th>
          <th>{{ m.lexicon.cols.ending }}</th><th>{{ m.lexicon.cols.plural }}</th><th>{{ m.lexicon.cols.status }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in filtered" :key="e.id">
          <td class="ar lemma" lang="ar">{{ e.lemma }}</td>
          <td>{{ e.gloss_en }}<div class="small muted">{{ m.grammar.gender[e.gender] }}</div></td>
          <td>{{ m.grammar.pos[e.pos] ?? e.pos }}</td>
          <td>
            {{ m.grammar.finalClass[e.final_class] ?? e.final_class }}
            <div v-if="e.alif_origin" class="small muted">{{ m.lexicon.alifOrigin }}: {{ e.alif_origin === "waw" ? "و" : "ي" }}</div>
            <div v-if="e.hamza_type" class="small muted">{{ m.lexicon.hamza }}: {{ e.hamza_type }}</div>
            <div v-if="e.diptote" class="small muted">{{ m.lexicon.diptote }}</div>
          </td>
          <td>
            <div v-for="(p, i) in e.plurals" :key="i">
              <span v-if="p.form" class="ar plural" lang="ar">{{ p.form }}</span>
              <span class="small muted"> {{ m.grammar.kind[p.kind] }}</span>
            </div>
            <span v-if="!e.plurals.length" class="small muted">—</span>
          </td>
          <td><span class="badge" :class="e.verified ? 'ok' : 'warn'">{{ e.verified ? m.lexicon.verified : m.lexicon.unverified }}</span></td>
        </tr>
        <tr v-if="!filtered.length"><td colspan="6" class="muted">{{ m.lexicon.nothing }}</td></tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.search { width: 100%; max-width: 420px; margin: 12px 0 16px; }
.lex { padding: 0; }
.lemma { font-size: 26px; white-space: nowrap; }
.plural { font-size: 20px; }
</style>
