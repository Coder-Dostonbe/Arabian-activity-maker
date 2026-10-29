<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { engine, type Rule } from "../engine";
import { useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";
import { useResultsStore, type Run } from "../stores/results";
import { arClass, textDir } from "../util";

const m = useI18n();
const results = useResultsStore();
const store = useEngineStore();

const group = ref("");
const openId = ref<string | null>(null);
const confirmId = ref<string | null>(null);
const rules = ref<Rule[]>([]);
const notice = ref<{ kind: "ok" | "err"; text: string } | null>(null);
const exporting = ref(false);

onMounted(async () => {
  try {
    rules.value = await store.loadRules();
  } catch {
    /* rule names are optional here */
  }
});

const shown = computed(() => results.runs.filter((r) => !group.value || r.group === group.value));
const stats = computed(() => results.ruleStats(shown.value));
const ruleName = (id: string) => rules.value.find((r) => r.id === id)?.name_ar ?? id;

function date(ms: number) {
  return new Date(ms).toLocaleString();
}

function percent(n: number, of: number) {
  return of ? Math.round((n / of) * 100) : 0;
}

function remove(run: Run) {
  if (confirmId.value !== run.id) {
    confirmId.value = run.id;
    return;
  }
  results.remove(run.id);
  confirmId.value = null;
}

function outcomeLabel(o: string) {
  return { correct: m.value.common.correct, wrong: m.value.common.wrong, skipped: m.value.common.skipped }[o] ?? m.value.test.unanswered;
}

async function exportXlsx() {
  const c = m.value.results.cols;
  const runs = shown.value;
  const sheets: Record<string, string[][]> = {
    [m.value.results.sheets.runs]: [
      [c.date, c.set, c.group, c.correct, c.wrong, c.unanswered, c.total, c.score],
      ...runs.map((r) => [date(r.date), r.setName, r.group, `${r.correct}`, `${r.wrong}`, `${r.unanswered}`, `${r.total}`, `${percent(r.correct, r.total)}%`]),
    ],
    [m.value.results.sheets.questions]: [
      [c.date, c.group, c.question, c.answer, c.outcome, c.rule],
      ...runs.flatMap((r) => r.questions.map((q) => [date(r.date), r.group, q.shown, q.answer, outcomeLabel(q.outcome), q.rules[0] ?? ""])),
    ],
    [m.value.results.sheets.rules]: [
      [c.rule, c.ruleName, c.asked, c.wrong, c.errorRate],
      ...stats.value.map((s) => [s.rule, ruleName(s.rule), `${s.asked}`, `${s.wrong}`, `${percent(s.wrong, s.asked)}%`]),
    ],
  };
  exporting.value = true;
  notice.value = null;
  try {
    const { data } = await engine.exportXlsx(sheets);
    const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
    const path = await invoke<string>("export_file", { fileName: `ArabMorph-results-${stamp}.xlsx`, data });
    notice.value = { kind: "ok", text: m.value.results.exported(path) };
  } catch (e) {
    notice.value = { kind: "err", text: (e as Error).message ?? String(e) };
  } finally {
    exporting.value = false;
  }
}
</script>

<template>
  <section>
    <h1>{{ m.results.title }}</h1>
    <p class="muted intro">{{ m.results.intro }}</p>

    <div class="toolbar">
      <label class="field inline">
        <span class="small muted">{{ m.results.group }}</span>
        <select v-model="group">
          <option value="">{{ m.results.allGroups }}</option>
          <option v-for="g in results.groups" :key="g" :value="g">{{ g }}</option>
        </select>
      </label>
      <span class="spacer" />
      <button :disabled="!shown.length || exporting || !isTauri()" @click="exportXlsx">{{ m.results.export }}</button>
    </div>
    <div v-if="notice" class="notice" :class="notice.kind">{{ notice.text }}</div>

    <p v-if="!shown.length" class="notice">{{ m.results.empty }}</p>
    <template v-else>
      <div class="panel">
        <table>
          <thead>
            <tr>
              <th>{{ m.results.cols.date }}</th><th>{{ m.results.cols.set }}</th><th>{{ m.results.cols.group }}</th>
              <th>{{ m.results.cols.score }}</th><th />
            </tr>
          </thead>
          <tbody>
            <template v-for="r in shown" :key="r.id">
              <tr class="run" @click="openId = openId === r.id ? null : r.id">
                <td>{{ date(r.date) }}</td>
                <td :dir="textDir(r.setName)">{{ r.setName }}</td>
                <td>{{ r.group || "—" }}</td>
                <td>
                  <span class="badge ok">✓ {{ r.correct }}</span>
                  <span class="badge err">✗ {{ r.wrong }}</span>
                  <span class="muted small">/ {{ r.total }} · {{ percent(r.correct, r.total) }}%</span>
                </td>
                <td class="end">
                  <button class="small-btn" @click.stop="remove(r)">{{ confirmId === r.id ? m.results.confirmDelete : m.common.delete }}</button>
                </td>
              </tr>
              <tr v-if="openId === r.id">
                <td colspan="5">
                  <table class="inner">
                    <tbody>
                      <tr v-for="(q, i) in r.questions" :key="i">
                        <td class="muted">{{ i + 1 }}</td>
                        <td :class="arClass(q.shown)" class="cell-big">{{ q.shown }}</td>
                        <td :class="arClass(q.answer)" class="cell-big">{{ q.answer }}</td>
                        <td>
                          <span class="badge" :class="{ ok: q.outcome === 'correct', err: q.outcome === 'wrong', warn: q.outcome === 'skipped' }">
                            {{ outcomeLabel(q.outcome) }}
                          </span>
                        </td>
                        <td class="ar small">{{ q.rules[0] ? ruleName(q.rules[0]) : "" }}</td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="panel">
        <h2>{{ m.results.byRule }}</h2>
        <p class="small muted">{{ m.results.byRuleHint }}</p>
        <p v-if="!stats.length" class="small muted">{{ m.results.noRules }}</p>
        <table v-else>
          <thead>
            <tr><th>{{ m.results.cols.ruleName }}</th><th>{{ m.results.cols.asked }}</th><th>{{ m.results.cols.wrong }}</th><th>{{ m.results.cols.errorRate }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in stats" :key="s.rule">
              <td><span class="ar">{{ ruleName(s.rule) }}</span> <span class="muted small">{{ s.rule }}</span></td>
              <td>{{ s.asked }}</td>
              <td>{{ s.wrong }}</td>
              <td>
                <div class="rate"><div class="fill" :style="{ inlineSize: `${percent(s.wrong, s.asked)}%` }" /></div>
                {{ percent(s.wrong, s.asked) }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.intro { max-width: 760px; }
.toolbar { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 8px; margin: 12px 0; }
.spacer { flex: 1; }
.field.inline { display: flex; flex-direction: column; gap: 2px; }
.panel { margin-top: 12px; overflow-x: auto; }
.run { cursor: pointer; }
.end { text-align: end; }
.inner { margin: 4px 0 8px; }
.cell-big.ar { font-size: 22px; }
.small-btn { font-size: 12px; padding: 4px 10px; }
.rate { display: inline-block; inline-size: 80px; block-size: 8px; background: var(--surface-2); border-radius: 4px; vertical-align: middle; margin-inline-end: 6px; overflow: hidden; }
.rate .fill { block-size: 100%; background: var(--err); }
</style>
