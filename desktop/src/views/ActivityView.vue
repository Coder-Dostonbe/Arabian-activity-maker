<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import SetPicker from "../components/SetPicker.vue";
import { useCountdown } from "../composables/countdown";
import { useI18n } from "../i18n";
import { useSetsStore, type Item } from "../stores/sets";
import { arClass, textDir, persisted, shuffle } from "../util";

type Outcome = "correct" | "wrong" | "timeout";
type Phase = "setup" | "show" | "reveal" | "done";

const REVEAL_MS = 2000;

const m = useI18n();
const sets = useSetsStore();
const timer = useCountdown();

const setId = persisted<string | null>("arabmorph.activity.set", null);
const seconds = persisted("arabmorph.activity.seconds", 5);
const mix = persisted("arabmorph.activity.shuffle", true);
const reveal = persisted("arabmorph.activity.reveal", false);

const phase = ref<Phase>("setup");
const paused = ref(false);
const queue = ref<Item[]>([]);
const index = ref(0);
const results = ref<{ item: Item; outcome: Outcome }[]>([]);

const current = computed(() => queue.value[index.value]);
const secondsLeft = computed(() => Math.ceil(timer.remaining.value / 1000));
const fraction = computed(() => (timer.total.value ? timer.remaining.value / timer.total.value : 0));
const counts = computed(() => ({
  correct: results.value.filter((r) => r.outcome === "correct").length,
  wrong: results.value.filter((r) => r.outcome === "wrong").length,
  timeout: results.value.filter((r) => r.outcome === "timeout").length,
}));
const misses = computed(() => results.value.filter((r) => r.outcome !== "correct"));

function begin(items: Item[]) {
  if (!items.length) return;
  queue.value = mix.value ? shuffle(items) : items.slice();
  index.value = 0;
  results.value = [];
  paused.value = false;
  show();
}

function startFromSet() {
  const set = sets.get(setId.value);
  seconds.value = Math.min(120, Math.max(1, Math.round(seconds.value || 5)));
  if (set) begin(set.items.filter((i) => i.approved));
}

function show() {
  phase.value = "show";
  timer.start(seconds.value * 1000, () => mark("timeout"));
}

function mark(outcome: Outcome) {
  if (phase.value !== "show" || paused.value) return;
  timer.stop();
  results.value.push({ item: current.value, outcome });
  if (reveal.value && current.value.answer) {
    phase.value = "reveal";
    timer.start(REVEAL_MS, advance);
  } else {
    advance();
  }
}

function advance() {
  index.value++;
  if (index.value >= queue.value.length) {
    timer.stop();
    phase.value = "done";
  } else {
    show();
  }
}

function togglePause() {
  if (phase.value !== "show" && phase.value !== "reveal") return;
  paused.value = !paused.value;
  if (paused.value) timer.pause();
  else timer.resume();
}

function stop() {
  timer.stop();
  phase.value = results.value.length ? "done" : "setup";
}

function onKey(e: KeyboardEvent) {
  if (phase.value !== "show" && phase.value !== "reveal") return;
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
  if (e.key === "1") mark("correct");
  else if (e.key === "2") mark("wrong");
  else if (e.key === " ") togglePause();
  else if (e.key === "Escape") stop();
  else return;
  e.preventDefault();
}

onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <section>
    <template v-if="phase === 'setup'">
      <h1>{{ m.activity.title }}</h1>
      <p class="muted intro">{{ m.activity.intro }}</p>
      <div class="panel setup">
        <SetPicker v-model="setId" />
        <div class="row">
          <label class="field">
            <span class="small muted">{{ m.activity.perWord }}</span>
            <span class="with-unit"><input v-model.number="seconds" type="number" min="1" max="120" class="num" /> {{ m.common.seconds }}</span>
          </label>
        </div>
        <label class="check"><input v-model="mix" type="checkbox" /> {{ m.common.shuffle }}</label>
        <label class="check"><input v-model="reveal" type="checkbox" /> {{ m.activity.reveal }}</label>
        <div>
          <button class="primary big" :disabled="!setId" @click="startFromSet">{{ m.common.start }}</button>
        </div>
        <p class="small muted">{{ m.activity.keys }}</p>
      </div>
    </template>

    <div v-else-if="phase !== 'done' && current" class="stage">
      <div class="stage-top">
        <span class="muted">{{ m.activity.progress(index + 1, queue.length) }}</span>
        <span class="clock" :class="{ low: secondsLeft <= 2 && phase === 'show' }">{{ secondsLeft }}</span>
      </div>
      <div class="bar"><div class="fill" :class="{ reveal: phase === 'reveal' }" :style="{ inlineSize: `${fraction * 100}%` }" /></div>

      <div class="card">
        <div v-if="current.note" class="note" :class="arClass(current.note)">{{ current.note }}</div>
        <div class="prompt" :class="arClass(current.prompt)" :dir="textDir(current.prompt)">{{ current.prompt }}</div>
        <div v-if="phase === 'reveal'" class="answer" :class="arClass(current.answer)" :dir="textDir(current.answer)">{{ current.answer }}</div>
        <div v-if="paused" class="paused-badge">{{ m.common.paused }}</div>
      </div>

      <div class="controls">
        <button class="ok big" :disabled="phase !== 'show' || paused" @click="mark('correct')">✓ {{ m.common.correct }}</button>
        <button class="bad big" :disabled="phase !== 'show' || paused" @click="mark('wrong')">✗ {{ m.common.wrong }}</button>
      </div>
      <div class="controls secondary">
        <button @click="togglePause">{{ paused ? m.common.resume : m.common.pause }}</button>
        <button @click="stop">{{ m.common.stop }}</button>
      </div>
      <p class="small muted center">{{ m.activity.keys }}</p>
    </div>

    <template v-else-if="phase === 'done'">
      <h1>{{ m.activity.finished }}</h1>
      <div class="tiles">
        <div class="tile ok"><div class="n">{{ counts.correct }}</div>{{ m.common.correct }}</div>
        <div class="tile bad"><div class="n">{{ counts.wrong }}</div>{{ m.common.wrong }}</div>
        <div class="tile"><div class="n">{{ counts.timeout }}</div>{{ m.common.timedOut }}</div>
      </div>
      <div class="panel">
        <template v-if="misses.length">
          <h2>{{ m.activity.mistakes }}</h2>
          <table>
            <tbody>
              <tr v-for="(r, i) in misses" :key="i">
                <td :class="arClass(r.item.prompt)" class="cell-big">{{ r.item.prompt }}</td>
                <td :class="arClass(r.item.answer)" class="cell-big">{{ r.item.answer }}</td>
                <td><span class="badge" :class="r.outcome === 'wrong' ? 'err' : 'warn'">{{ r.outcome === "wrong" ? m.common.wrong : m.common.timedOut }}</span></td>
              </tr>
            </tbody>
          </table>
        </template>
        <p v-else class="notice ok">{{ m.activity.noMistakes }}</p>
      </div>
      <div class="actions">
        <button v-if="misses.length" class="primary" @click="begin(misses.map((r) => r.item))">{{ m.activity.repeat }}</button>
        <button @click="begin(queue)">{{ m.common.restart }}</button>
        <button @click="phase = 'setup'">{{ m.common.settings }}</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.intro { max-width: 760px; }
.setup { display: flex; flex-direction: column; gap: 14px; margin-top: 16px; max-width: 560px; }
.row { display: flex; flex-wrap: wrap; gap: 14px; }

.stage { display: flex; flex-direction: column; gap: 14px; max-width: 980px; margin: 0 auto; }
.stage-top { display: flex; justify-content: space-between; align-items: baseline; font-size: 18px; }
.clock { font-size: 40px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--accent); }
.clock.low { color: var(--err); }
.bar { block-size: 8px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
.fill { block-size: 100%; background: var(--accent); transition: inline-size .1s linear; }
.fill.reveal { background: var(--ok); }

.card {
  position: relative; min-block-size: 46vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 18px; padding: 32px; text-align: center;
  background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
}
.prompt { font-size: clamp(48px, 9vw, 120px); line-height: 1.3; word-break: break-word; }
.prompt:not(.ar) { font-size: clamp(30px, 5vw, 56px); }
.note { font-size: 20px; color: var(--muted); }
.answer { font-size: clamp(36px, 6vw, 80px); color: var(--ok); }
.answer:not(.ar) { font-size: clamp(24px, 4vw, 44px); }
.paused-badge {
  position: absolute; inset-block-start: 14px; inset-inline-end: 14px;
  background: var(--warn-soft); color: var(--warn); padding: 4px 12px; border-radius: 12px; font-weight: 600;
}
.controls { display: flex; justify-content: center; gap: 14px; flex-wrap: wrap; }
.center { text-align: center; }

.tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 16px 0; max-width: 640px; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px; text-align: center; }
.tile .n { font-size: 36px; font-weight: 700; }
.tile.ok .n { color: var(--ok); }
.tile.bad .n { color: var(--err); }
.cell-big.ar { font-size: 26px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
</style>
