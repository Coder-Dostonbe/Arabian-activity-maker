<script setup lang="ts">
import { computed, ref } from "vue";
import { ClaudeError, draftItems, MAX_DRAFT_ITEMS } from "../claude";
import { engine, type BuildResult, type CaseName, type NumberName, type StateName } from "../engine";
import { useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";
import { useSetsStore, type WordSet } from "../stores/sets";
import { persisted, readStorage, writeStorage } from "../util";

// Generates rows for one set: offline with the engine, or online with Claude.
const props = defineProps<{ set: WordSet }>();
const m = useI18n();
const sets = useSetsStore();
const store = useEngineStore();

const MAX_WORDS = 200;
const KEY_STORE = "arabmorph.claude.key";

const tab = persisted<"engine" | "claude">("arabmorph.assistant.tab", "engine");

// --- engine ---
const words = ref("");
const number = persisted<NumberName>("arabmorph.assistant.number", "dual");
const kase = persisted<CaseName>("arabmorph.assistant.case", "nominative");
const state = persisted<StateName>("arabmorph.assistant.state", "indefinite");
const busy = ref(false);
const message = ref<string | null>(null);
const failure = ref<string | null>(null);
const skipped = ref<BuildResult["skipped"]>([]);

const wordList = computed(() => [...new Set(words.value.split(/[\n,،]+/).map((w) => w.trim()).filter(Boolean))]);

function fromSet() {
  words.value = [...new Set(props.set.items.map((i) => i.prompt).filter((p) => /[؀-ۿ]/.test(p) && !/\s/.test(p)))].join("\n");
}

async function fromLexicon() {
  try {
    const lex = await store.loadLexicon();
    words.value = lex.map((e) => e.lemma).join("\n");
  } catch (e) {
    failure.value = (e as Error).message;
  }
}

function note() {
  const g = m.value.grammar;
  return [g.number[number.value], g.case[kase.value], g.state[state.value]].join(" · ");
}

async function runEngine() {
  const list = wordList.value;
  if (!list.length) return;
  if (list.length > MAX_WORDS) {
    failure.value = m.value.gen.tooMany(MAX_WORDS);
    return;
  }
  busy.value = true;
  message.value = failure.value = null;
  skipped.value = [];
  try {
    const r = await engine.buildItems({ words: list, number: number.value, case: kase.value, state: state.value });
    const n = note();
    sets.append(props.set.id, r.items.map((i) => ({ prompt: i.prompt, answer: i.answer, note: n, options: i.options, uncertain: i.uncertain })), "engine");
    skipped.value = r.skipped;
    message.value = m.value.gen.added(r.items.length);
  } catch (e) {
    failure.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

// --- Claude ---
const savedKey = readStorage<string>(KEY_STORE, "");
const apiKey = ref(savedKey);
const remember = ref(!!savedKey);
const topic = ref("");
const count = ref(10);

async function runClaude() {
  const key = apiKey.value.trim();
  if (!key || !topic.value.trim()) return;
  if (remember.value) writeStorage(KEY_STORE, key);
  else writeStorage(KEY_STORE, "");
  busy.value = true;
  message.value = failure.value = null;
  skipped.value = [];
  try {
    const n = Math.min(MAX_DRAFT_ITEMS, Math.max(1, Math.round(count.value || 10)));
    const items = await draftItems(key, topic.value.trim(), n, m.value.claudeLanguage);
    sets.append(props.set.id, items, "claude");
    message.value = m.value.gen.added(items.length);
  } catch (e) {
    if (e instanceof ClaudeError) {
      const text = m.value.gen.claudeErrors[e.kind] ?? m.value.gen.claudeErrors.other;
      failure.value = e.message ? `${text} ${e.message}` : text;
    } else {
      failure.value = (e as Error).message;
    }
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="panel assistant">
    <div class="head">
      <h2>{{ m.gen.title }}</h2>
      <div class="tabs" role="tablist">
        <button role="tab" :aria-selected="tab === 'engine'" :class="{ on: tab === 'engine' }" @click="tab = 'engine'">{{ m.gen.engineTab }}</button>
        <button role="tab" :aria-selected="tab === 'claude'" :class="{ on: tab === 'claude' }" @click="tab = 'claude'">{{ m.gen.claudeTab }}</button>
      </div>
    </div>
    <p class="small muted">{{ m.gen.needSet }}</p>

    <form v-if="tab === 'engine'" class="form" @submit.prevent="runEngine">
      <p class="muted">{{ m.gen.engineIntro }}</p>
      <label class="field">
        <span class="small muted">{{ m.gen.words }} ({{ wordList.length }})</span>
        <textarea v-model="words" rows="5" class="ar words" lang="ar" dir="rtl" :placeholder="m.gen.wordsPlaceholder" />
      </label>
      <div class="row">
        <button type="button" class="small-btn" @click="fromSet">{{ m.gen.fromSet }}</button>
        <button type="button" class="small-btn" @click="fromLexicon">{{ m.gen.fromLexicon }}</button>
      </div>
      <div class="row">
        <label class="field">
          <span class="small muted">{{ m.gen.form }}</span>
          <select v-model="number">
            <option v-for="(label, k) in m.grammar.number" :key="k" :value="k">{{ label }}</option>
          </select>
        </label>
        <label class="field">
          <span class="small muted">&nbsp;</span>
          <select v-model="kase">
            <option v-for="(label, k) in m.grammar.case" :key="k" :value="k">{{ label }}</option>
          </select>
        </label>
        <label class="field">
          <span class="small muted">&nbsp;</span>
          <select v-model="state">
            <option v-for="(label, k) in m.grammar.state" :key="k" :value="k">{{ label }}</option>
          </select>
        </label>
      </div>
      <div>
        <button class="primary" type="submit" :disabled="busy || !wordList.length || store.error !== null">
          {{ busy ? m.gen.generating : m.gen.generate }}
        </button>
      </div>
    </form>

    <form v-else class="form" @submit.prevent="runClaude">
      <p class="muted">{{ m.gen.claudeIntro }}</p>
      <label class="field">
        <span class="small muted">{{ m.gen.apiKey }}</span>
        <input v-model="apiKey" type="password" autocomplete="off" spellcheck="false" placeholder="sk-ant-…" />
      </label>
      <label class="check"><input v-model="remember" type="checkbox" /> {{ m.gen.remember }}</label>
      <p v-if="remember" class="small muted">{{ m.gen.rememberHint }}</p>
      <label class="field">
        <span class="small muted">{{ m.gen.topic }}</span>
        <textarea v-model="topic" rows="3" dir="auto" :placeholder="m.gen.topicPlaceholder" />
      </label>
      <label class="field">
        <span class="small muted">{{ m.gen.count }}</span>
        <input v-model.number="count" type="number" min="1" :max="MAX_DRAFT_ITEMS" class="num" />
      </label>
      <div>
        <button class="primary" type="submit" :disabled="busy || !apiKey.trim() || !topic.trim()">
          {{ busy ? m.gen.generating : m.gen.generate }}
        </button>
      </div>
    </form>

    <div v-if="message" class="notice ok">{{ message }}</div>
    <div v-if="failure" class="notice err">{{ failure }}</div>
    <div v-if="skipped.length" class="skipped">
      <h3 class="small">{{ m.gen.skippedTitle }}</h3>
      <ul class="plain">
        <li v-for="s in skipped" :key="s.word" class="small">
          <span class="ar word">{{ s.word }}</span> — {{ m.gen.reason[s.reason] }}
          <span v-if="s.reason === 'ambiguous'" class="ar">({{ s.detail }})</span>
          <span v-else class="muted">{{ s.detail }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.assistant { display: flex; flex-direction: column; gap: 10px; }
.head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.head h2 { margin: 0; }
.tabs { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.tabs button { border: 0; border-radius: 0; border-inline-end: 1px solid var(--border); }
.tabs button:last-child { border-inline-end: 0; }
.tabs button.on { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.form { display: flex; flex-direction: column; gap: 10px; }
.row { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
.words { font-size: 22px; }
.small-btn { font-size: 12px; padding: 4px 10px; }
.skipped h3 { margin: 6px 0 4px; }
.skipped .ar { font-size: 18px; }
</style>
