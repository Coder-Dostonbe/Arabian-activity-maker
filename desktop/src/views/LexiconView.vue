<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { LexiconEntry } from "../engine";
import { finalClassLabel, genderLabel, kindLabel, posLabel } from "../labels";
import { useEngineStore } from "../stores/engine";

const store = useEngineStore();
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
    <h1>Lug'at</h1>
    <p class="muted">
      Qoidalar imlodan aniqlay olmaydigan ma'lumotlar: alifning asli, hamza turi, mamnu' min as-sarf va ko'plik turlari.
      Barcha yozuvlar hali mutaxassis tomonidan tekshirilmagan.
    </p>
    <input v-model="query" type="search" class="search" placeholder="Qidirish: arabcha yoki inglizcha ma'no…" aria-label="Lug'atdan qidirish" />
    <div v-if="failure" class="notice err">{{ failure }}</div>
    <table v-else class="panel lex">
      <thead>
        <tr><th>So'z</th><th>Ma'nosi</th><th>Turkum</th><th>Oxiri</th><th>Ko'plik</th><th>Holat</th></tr>
      </thead>
      <tbody>
        <tr v-for="e in filtered" :key="e.id">
          <td class="ar lemma" lang="ar">{{ e.lemma }}</td>
          <td>{{ e.gloss_en }}<div class="small muted">{{ genderLabel[e.gender] }}</div></td>
          <td>{{ posLabel[e.pos] ?? e.pos }}</td>
          <td>
            {{ finalClassLabel[e.final_class] ?? e.final_class }}
            <div v-if="e.alif_origin" class="small muted">alif asli: {{ e.alif_origin === "waw" ? "و" : "ي" }}</div>
            <div v-if="e.hamza_type" class="small muted">hamza: {{ e.hamza_type }}</div>
            <div v-if="e.diptote" class="small muted">mamnu' min as-sarf</div>
          </td>
          <td>
            <div v-for="(p, i) in e.plurals" :key="i">
              <span v-if="p.form" class="ar plural" lang="ar">{{ p.form }}</span>
              <span class="small muted"> {{ kindLabel[p.kind] }}</span>
            </div>
            <span v-if="!e.plurals.length" class="small muted">—</span>
          </td>
          <td><span class="badge" :class="e.verified ? 'ok' : 'warn'">{{ e.verified ? "Tekshirilgan" : "Tekshirilmagan" }}</span></td>
        </tr>
        <tr v-if="!filtered.length"><td colspan="6" class="muted">Hech narsa topilmadi.</td></tr>
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
