<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AssistantPanel from "../components/AssistantPanel.vue";
import { engine, EngineError } from "../engine";
import { useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";
import { useSetsStore, type Item } from "../stores/sets";
import { recovered } from "../storage";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { arClass, textDir, fileToBase64, persisted } from "../util";

const m = useI18n();
const sets = useSetsStore();
const store = useEngineStore();

const selectedId = persisted<string | null>("arabmorph.sets.selected", null);
const selected = computed(() => sets.get(selectedId.value));
const fileInput = ref<HTMLInputElement | null>(null);
const backupInput = ref<HTMLInputElement | null>(null);
const importing = ref(false);
const notices = ref<{ kind: "ok" | "warn" | "err"; text: string }[]>([]);
const confirmDelete = ref(false);

watch(() => sets.sets.length, () => {
  if (!selected.value) selectedId.value = sets.sets[0]?.id ?? null;
}, { immediate: true });
watch(selectedId, () => (confirmDelete.value = false));

const approvedCount = computed(() => selected.value?.items.filter((i) => i.approved).length ?? 0);

async function onFile(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  importing.value = true;
  notices.value = [];
  try {
    const r = await engine.importFile(file.name, await fileToBase64(file));
    let rows = 0;
    for (const s of r.sets) {
      const created = sets.create(s.name, s.items, "file");
      if (s === r.sets[0]) selectedId.value = created.id;
      rows += s.items.length;
    }
    notices.value.push({ kind: "ok", text: m.value.sets.imported(rows, r.sets.length) });
    for (const w of r.warnings) notices.value.push({ kind: "warn", text: m.value.sets.warnings[w] ?? w });
  } catch (err) {
    const code = err instanceof EngineError ? err.code : "";
    notices.value.push({ kind: "err", text: m.value.sets.errors[code] ?? (err as Error).message });
  } finally {
    importing.value = false;
  }
}

async function exportAll() {
  notices.value = [];
  try {
    const path = await invoke<string>("backup_export", { contents: sets.exportBackup() });
    notices.value.push({ kind: "ok", text: m.value.sets.exported(path) });
  } catch (err) {
    notices.value.push({ kind: "err", text: String(err) });
  }
}

async function onBackup(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  notices.value = [];
  const count = file.size > 32 * 1024 * 1024 ? null : sets.importBackup(await file.text());
  if (count === null) {
    notices.value.push({ kind: "err", text: m.value.sets.backupInvalid });
    return;
  }
  selectedId.value = sets.sets[0]?.id ?? null;
  notices.value.push({ kind: "ok", text: m.value.sets.restored(count) });
}

function newSet() {
  selectedId.value = sets.create(m.value.sets.newSetName).id;
}

function addRow() {
  if (selected.value) sets.append(selected.value.id, [{ prompt: "", answer: "", note: "", translation: "", options: [] }], "manual");
}

function removeRow(item: Item) {
  if (selected.value) selected.value.items = selected.value.items.filter((i) => i.id !== item.id);
}

function setAll(approved: boolean) {
  selected.value?.items.forEach((i) => (i.approved = approved));
}

function deleteSet() {
  if (!selected.value) return;
  sets.remove(selected.value.id);
  selectedId.value = sets.sets[0]?.id ?? null;
}

function optionsText(item: Item) {
  return item.options.join(" | ");
}

function setOptions(item: Item, text: string) {
  item.options = [...new Set(text.split("|").map((o) => o.trim()).filter(Boolean))];
}
</script>

<template>
  <section>
    <h1>{{ m.sets.title }}</h1>
    <p class="muted intro">{{ m.sets.intro }}</p>

    <div class="toolbar">
      <button class="primary" :disabled="importing || store.error !== null" @click="fileInput?.click()">
        {{ importing ? m.sets.importing : m.sets.import }}
      </button>
      <input ref="fileInput" type="file" hidden accept=".docx,.xlsx,.xlsm,.txt,.csv,.tsv" @change="onFile" />
      <button @click="newSet">{{ m.sets.newSet }}</button>
      <span class="spacer" />
      <button :disabled="!isTauri() || !sets.sets.length" @click="exportAll">{{ m.sets.exportAll }}</button>
      <button @click="backupInput?.click()">{{ m.sets.importBackup }}</button>
      <input ref="backupInput" type="file" hidden accept=".json,application/json" @change="onBackup" />
    </div>
    <div v-if="recovered" class="notice warn">{{ m.sets.recovered }}</div>
    <div v-for="(n, i) in notices" :key="i" class="notice" :class="n.kind">{{ n.text }}</div>
    <div v-if="sets.saveFailed" class="notice err">{{ m.sets.saveFailed }}</div>

    <details class="panel format">
      <summary>{{ m.sets.format.title }}</summary>
      <ul>
        <li v-for="line in m.sets.format.lines" :key="line">{{ line }}</li>
      </ul>
      <pre class="example" dir="auto">{{ m.sets.format.example }}</pre>
    </details>

    <p v-if="!sets.sets.length" class="muted">{{ m.sets.none }}</p>

    <div v-else class="layout">
      <ul class="plain set-list">
        <li v-for="s in sets.sets" :key="s.id">
          <button class="set-btn" :class="{ on: s.id === selectedId }" @click="selectedId = s.id">
            <span class="set-name">{{ s.name }}</span>
            <span class="small muted">{{ m.common.approvedOf(s.items.filter((i) => i.approved).length, s.items.length) }}</span>
          </button>
        </li>
      </ul>

      <div v-if="selected" class="editor">
        <div class="panel">
          <div class="editor-head">
            <label class="field name">
              <span class="small muted">{{ m.sets.name }}</span>
              <input v-model="selected.name" type="text" dir="auto" />
            </label>
            <span class="small muted">{{ m.common.approvedOf(approvedCount, selected.items.length) }}</span>
          </div>
          <div class="toolbar">
            <button @click="setAll(true)">{{ m.sets.approveAll }}</button>
            <button @click="setAll(false)">{{ m.sets.unapproveAll }}</button>
            <button @click="addRow">{{ m.sets.addRow }}</button>
            <span class="spacer" />
            <template v-if="!confirmDelete">
              <button class="danger" @click="confirmDelete = true">{{ m.sets.deleteSet }}</button>
            </template>
            <template v-else>
              <span class="small">{{ m.sets.deleteQuestion }}</span>
              <button class="danger solid" @click="deleteSet">{{ m.sets.confirmDelete }}</button>
              <button @click="confirmDelete = false">{{ m.common.cancel }}</button>
            </template>
          </div>

          <p v-if="!selected.items.length" class="muted">{{ m.sets.noItems }}</p>
          <div v-else class="table-wrap">
            <table class="items">
              <thead>
                <tr>
                  <th>{{ m.sets.approved }}</th>
                  <th>{{ m.sets.prompt }}</th>
                  <th>{{ m.sets.translation }}</th>
                  <th>{{ m.common.answer }}</th>
                  <th>{{ m.common.note }}</th>
                  <th>{{ m.sets.options }}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in selected.items" :key="item.id" :class="{ pending: !item.approved }">
                  <td class="center"><input v-model="item.approved" type="checkbox" :aria-label="m.sets.approved" /></td>
                  <td><input v-model="item.prompt" type="text" :class="arClass(item.prompt)" :dir="textDir(item.prompt)" /></td>
                  <td><input v-model="item.translation" type="text" :class="arClass(item.translation)" :dir="textDir(item.translation)" /></td>
                  <td><input v-model="item.answer" type="text" :class="arClass(item.answer)" :dir="textDir(item.answer)" /></td>
                  <td><input v-model="item.note" type="text" :dir="textDir(item.note)" /></td>
                  <td>
                    <input :value="optionsText(item)" type="text" :class="arClass(optionsText(item))" :dir="textDir(optionsText(item))"
                           @change="setOptions(item, ($event.target as HTMLInputElement).value)" />
                  </td>
                  <td class="meta">
                    <span v-if="item.form" class="badge accent" :title="item.base">{{ m.sets.forms[item.form] }}</span>
                    <span class="badge">{{ m.sets.origin[item.origin] }}</span>
                    <span v-if="item.uncertain" class="badge warn">{{ m.sets.uncertain }}</span>
                    <button class="icon" :aria-label="m.common.delete" :title="m.common.delete" @click="removeRow(item)">✕</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <AssistantPanel :set="selected" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.intro { max-width: 820px; }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 12px 0; }
.spacer { flex: 1; }
.format { margin-bottom: 16px; }
.format summary { cursor: pointer; font-weight: 600; }
.format ul { margin: 8px 0; padding-inline-start: 20px; }
.example {
  background: var(--surface-2); border-radius: 6px; padding: 10px 12px; margin: 0;
  font-family: var(--font-ar); font-size: 16px; white-space: pre-wrap;
}
.layout { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 16px; align-items: start; }
.set-list { display: flex; flex-direction: column; gap: 4px; }
.set-btn { inline-size: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: 2px; text-align: start; }
.set-btn.on { border-color: var(--accent); background: var(--accent-soft); }
.set-name { font-weight: 600; overflow-wrap: anywhere; }
.editor { display: flex; flex-direction: column; gap: 16px; min-inline-size: 0; }
.editor-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; }
.name { flex: 1; max-inline-size: 420px; }
.name input { inline-size: 100%; }
.table-wrap { overflow-x: auto; }
.items th, .items td { padding: 4px 6px; vertical-align: middle; }
.items input[type="text"] { inline-size: 100%; min-inline-size: 110px; padding: 4px 8px; }
.items input.ar { font-size: 20px; padding-block: 0; }
.items tr.pending td { background: var(--warn-soft); }
.center { text-align: center; }
.meta { white-space: nowrap; }
.meta .badge { margin-inline-end: 4px; }
.icon { border: 0; background: none; padding: 2px 6px; color: var(--muted); }
.icon:hover { color: var(--err); background: none; }
.danger { color: var(--err); }
.danger.solid { background: var(--err); border-color: var(--err); color: var(--on-accent); }
</style>
