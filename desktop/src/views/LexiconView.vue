<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { engine, type LexiconEntry } from "../engine";
import { useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";
import { toDraft, useLexiconQueue } from "../stores/lexiconQueue";

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

async function reload() {
  try {
    entries.value = await store.loadLexicon();
  } catch (e) {
    failure.value = (e as Error).message;
  }
}

// --- proposals awaiting review, and the teacher's own entries ---------------------
const queue = useLexiconQueue();
const problems = ref<Record<string, string[]>>({});
const queueMessage = ref<{ kind: "ok" | "err"; text: string } | null>(null);

async function checkAll() {
  for (const p of queue.items) {
    try {
      problems.value[p.id] = (await engine.checkEntry(toDraft(p.entry))).problems;
    } catch (e) {
      problems.value[p.id] = [(e as Error).message];
    }
  }
}

async function approve(id: string) {
  queueMessage.value = null;
  try {
    const r = await queue.approve(id);
    if (r) queueMessage.value = { kind: "ok", text: m.value.queue.added(r.entry.lemma, r.homographs) };
    await reload();
  } catch (e) {
    queueMessage.value = { kind: "err", text: (e as Error).message };
  }
}

async function removeUser(e: LexiconEntry) {
  try {
    await engine.removeEntry(e.id);
    store.lexicon = null;
    await reload();
  } catch (err) {
    failure.value = (err as Error).message;
  }
}

onMounted(async () => {
  await reload();
  await checkAll();
});
</script>

<template>
  <section>
    <h1>{{ m.lexicon.title }}</h1>
    <p class="muted">{{ m.lexicon.intro }}</p>
    <div v-if="queue.items.length || queueMessage" class="panel queue">
      <h2>{{ m.queue.title }} <span class="muted small">({{ queue.items.length }})</span></h2>
      <p class="small muted">{{ m.queue.intro }}</p>
      <div v-if="queueMessage" class="notice" :class="queueMessage.kind">{{ queueMessage.text }}</div>
      <article v-for="p in queue.items" :key="p.id" class="proposal">
        <div class="head">
          <span class="ar lemma" lang="ar">{{ p.entry.lemma }}</span>
          <span class="muted small">{{ m.queue.asked(p.word, m.models.names[p.model] ?? p.model) }}</span>
        </div>
        <div class="small">
          {{ m.grammar.pos[p.entry.pos] ?? p.entry.pos }} · {{ m.grammar.gender[p.entry.gender] }} ·
          {{ m.grammar.finalClass[p.entry.final_class] ?? p.entry.final_class }}
          <span v-if="p.entry.alif_origin"> · {{ m.lexicon.alifOrigin }}: {{ p.entry.alif_origin }}</span>
          <span v-if="p.entry.hamza_type"> · {{ m.lexicon.hamza }}: {{ p.entry.hamza_type }}</span>
          <span v-if="p.entry.diptote"> · {{ m.lexicon.diptote }}</span>
          <span v-if="p.entry.gloss_en"> · {{ p.entry.gloss_en }}</span>
        </div>
        <div class="small">
          {{ m.lexicon.cols.plural }}:
          <span v-for="(pl, i) in p.entry.plurals" :key="i"><span v-if="pl.form" class="ar plural">{{ pl.form }}</span> {{ m.grammar.kind[pl.kind] }}; </span>
          <span v-if="!p.entry.plurals.length">—</span>
        </div>
        <p v-if="p.entry.note" class="small muted">{{ p.entry.note }}</p>
        <ul v-if="problems[p.id]?.length" class="small err-list">
          <li v-for="x in problems[p.id]" :key="x">{{ x }}</li>
        </ul>
        <div class="row">
          <button class="primary" :disabled="!!problems[p.id]?.length" @click="approve(p.id)">{{ m.queue.approve }}</button>
          <button @click="queue.reject(p.id)">{{ m.queue.reject }}</button>
        </div>
      </article>
    </div>

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
          <td>
            <span class="badge" :class="e.verified ? 'ok' : 'warn'">{{ e.verified ? m.lexicon.verified : m.lexicon.unverified }}</span>
            <template v-if="e.source === 'user'">
              <div class="small muted">{{ m.queue.mine }}</div>
              <button class="small-btn" @click="removeUser(e)">{{ m.common.delete }}</button>
            </template>
          </td>
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
.queue { margin: 12px 0; display: flex; flex-direction: column; gap: 10px; }
.proposal { border-top: 1px solid var(--border); padding-top: 10px; display: flex; flex-direction: column; gap: 6px; }
.proposal .head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.row { display: flex; gap: 8px; }
.err-list { color: var(--err); margin: 0; }
.small-btn { font-size: 12px; padding: 2px 8px; margin-top: 4px; }
</style>
