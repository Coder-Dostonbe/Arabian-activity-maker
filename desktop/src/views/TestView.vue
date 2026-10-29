<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import RuleHint from "../components/RuleHint.vue";
import SetPicker from "../components/SetPicker.vue";
import { useCountdown } from "../composables/countdown";
import { useI18n } from "../i18n";
import { askable, questions as buildQuestions, UZ_QUESTIONS, type Question } from "../exercise";
import { useResultsStore } from "../stores/results";
import { useSetsStore } from "../stores/sets";
import { arClass, textDir, beep, formatClock, persisted, shuffle } from "../util";

type Outcome = "correct" | "wrong" | "skipped";

const LETTERS = ["A", "B", "C", "D", "E", "F", "G"];

const m = useI18n();
const sets = useSetsStore();
const timer = useCountdown();

const setId = persisted<string | null>("arabmorph.test.set", null);
const minutes = persisted("arabmorph.test.minutes", 5);
const extraSeconds = persisted("arabmorph.test.seconds", 0);
const mix = persisted("arabmorph.test.shuffle", true);
const withOptions = persisted("arabmorph.test.options", true);
const sound = persisted("arabmorph.test.sound", true);
const group = persisted("arabmorph.test.group", "");
const results = useResultsStore();
const saved = ref(false);

const phase = ref<"setup" | "run" | "over">("setup");
const endReason = ref<"time" | "done">("time");
const paused = ref(false);
const questions = ref<Question[]>([]);
const index = ref(0);
const outcomes = ref<(Outcome | undefined)[]>([]);
const revealed = ref(false);
const chosen = ref<string | null>(null);

const approved = computed(() => sets.get(setId.value)?.items.filter((i) => i.approved) ?? []);
const answerable = computed(() => askable(approved.value));
const current = computed(() => questions.value[index.value]);
const decided = computed(() => outcomes.value[index.value] !== undefined);
const lowTime = computed(() => timer.remaining.value <= 10_000);
const counts = computed(() => {
  const c = { correct: 0, wrong: 0, unanswered: 0 };
  questions.value.forEach((_, i) => {
    const o = outcomes.value[i];
    if (o === "correct") c.correct++;
    else if (o === "wrong") c.wrong++;
    else c.unanswered++;
  });
  return c;
});

function begin() {
  const pool = answerable.value;
  if (!pool.length) return;
  minutes.value = Math.min(180, Math.max(0, Math.round(minutes.value || 0)));
  extraSeconds.value = Math.min(59, Math.max(0, Math.round(extraSeconds.value || 0)));
  const ms = (minutes.value * 60 + extraSeconds.value) * 1000;
  if (ms <= 0) return;
  const built = buildQuestions(pool, withOptions.value);
  questions.value = mix.value ? shuffle(built) : built;
  outcomes.value = [];
  index.value = 0;
  revealed.value = false;
  chosen.value = null;
  paused.value = false;
  saved.value = false;
  phase.value = "run";
  timer.start(ms, () => finish("time"));
}

function record(outcome: Outcome) {
  if (decided.value) return;
  outcomes.value[index.value] = outcome;
}

function choose(option: string) {
  if (revealed.value || paused.value) return;
  chosen.value = option;
  revealed.value = true;
  record(option === current.value.answer ? "correct" : "wrong");
}

function judge(outcome: "correct" | "wrong") {
  if (paused.value) return;
  record(outcome);
  next();
}

function skip() {
  if (paused.value) return;
  record("skipped");
  next();
}

function next() {
  if (paused.value) return;
  if (index.value + 1 >= questions.value.length) return finish("done");
  index.value++;
  revealed.value = false;
  chosen.value = null;
}

function finish(reason: "time" | "done") {
  timer.stop();
  endReason.value = reason;
  phase.value = "over";
  saveRun();
  if (reason === "time" && sound.value) beep();
}

/** Every finished test goes into the results history (Natijalar). */
function saveRun() {
  if (saved.value || !questions.value.length) return;
  const set = sets.get(setId.value);
  results.add({
    date: Date.now(),
    setId: set?.id ?? "",
    setName: set?.name ?? "",
    group: group.value.trim().slice(0, 80),
    correct: counts.value.correct,
    wrong: counts.value.wrong,
    unanswered: counts.value.unanswered,
    total: questions.value.length,
    questions: questions.value.map((q, i) => ({
      shown: q.shown,
      answer: q.answer,
      ask: q.ask,
      outcome: outcomes.value[i] ?? "unanswered",
      rules: q.item.rules ?? [],
    })),
  });
  saved.value = true;
}

function togglePause() {
  if (phase.value !== "run") return;
  paused.value = !paused.value;
  if (paused.value) timer.pause();
  else timer.resume();
}

// The rule behind the answer, after a wrong choice or "show answer", for rows the engine built.
const explain = computed(() => {
  const rules = current.value?.item.rules;
  if (!rules?.length || !revealed.value) return null;
  return !current.value.options || outcomes.value[index.value] === "wrong" ? rules : null;
});

function optionClass(option: string) {
  if (!revealed.value) return "";
  if (option === current.value.answer) return "is-right";
  return option === chosen.value ? "is-wrong" : "dim";
}

/** The Uzbek question line; a row whose prompt is already a written question needs none. */
function questionText(q: Question): string {
  return q.ask === "answer" && !arClass(q.shown) ? "" : UZ_QUESTIONS[q.ask];
}

function onKey(e: KeyboardEvent) {
  if (phase.value !== "run") return;
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
  const opts = current.value?.options;
  const n = Number(e.key);
  if (opts && n >= 1 && n <= opts.length) choose(opts[n - 1]);
  else if (e.key === "Enter" && decided.value) next();
  else if (e.key === " ") togglePause();
  else return;
  e.preventDefault();
}

onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <section>
    <template v-if="phase === 'setup'">
      <h1>{{ m.test.title }}</h1>
      <p class="muted intro">{{ m.test.intro }}</p>
      <div class="panel setup">
        <SetPicker v-model="setId" />
        <template v-if="setId">
          <p v-if="!answerable.length" class="notice warn">{{ m.test.noAnswers }}</p>
          <p v-else-if="answerable.length < approved.length" class="small muted">
            {{ m.test.withoutAnswer(approved.length - answerable.length) }}
          </p>
        </template>
        <label class="field">
          <span class="small muted">{{ m.test.totalTime }}</span>
          <span class="with-unit">
            <input v-model.number="minutes" type="number" min="0" max="180" class="num" /> {{ m.common.minutes }}
            <input v-model.number="extraSeconds" type="number" min="0" max="59" class="num" /> {{ m.common.seconds }}
          </span>
        </label>
        <label class="field">
          <span class="small muted">{{ m.results.group }}</span>
          <input v-model="group" type="text" maxlength="80" :placeholder="m.results.groupPlaceholder" />
        </label>
        <label class="check"><input v-model="mix" type="checkbox" /> {{ m.common.shuffle }}</label>
        <label class="check"><input v-model="withOptions" type="checkbox" /> {{ m.test.showOptions }}</label>
        <p v-if="withOptions" class="small muted hint">{{ m.test.optionsHint }}</p>
        <label class="check"><input v-model="sound" type="checkbox" /> {{ m.common.sound }}</label>
        <div>
          <button class="primary big" :disabled="!answerable.length || minutes * 60 + extraSeconds <= 0" @click="begin">
            {{ m.test.begin }}
          </button>
        </div>
      </div>
    </template>

    <div v-else-if="phase === 'run' && current" class="stage">
      <div class="stage-top">
        <span class="muted">{{ m.test.question(index + 1, questions.length) }}</span>
        <span class="score small">
          <span class="badge ok">✓ {{ counts.correct }}</span>
          <span class="badge err">✗ {{ counts.wrong }}</span>
        </span>
        <span class="clock" :class="{ low: lowTime }">{{ formatClock(timer.remaining.value) }}</span>
      </div>

      <div class="card">
        <div v-if="questionText(current)" class="question" lang="uz" dir="ltr">{{ questionText(current) }}</div>
        <div v-if="current.item.note && current.ask === 'answer'" class="note" :class="arClass(current.item.note)">{{ current.item.note }}</div>
        <div class="prompt" :class="arClass(current.shown)" :dir="textDir(current.shown)">{{ current.shown }}</div>
        <div v-if="revealed && !current.options" class="answer" :class="arClass(current.answer)" :dir="textDir(current.answer)">
          {{ current.answer }}
        </div>
        <div v-if="paused" class="paused-badge">{{ m.common.paused }}</div>
      </div>

      <RuleHint v-if="explain" :ids="explain" />

      <div v-if="current.options" class="options">
        <button v-for="(o, i) in current.options" :key="o" class="option" :class="optionClass(o)"
                :disabled="paused" @click="choose(o)">
          <span class="letter">{{ LETTERS[i] }}</span>
          <span :class="arClass(o)" :dir="textDir(o)">{{ o }}</span>
        </button>
      </div>

      <div class="controls">
        <template v-if="!current.options && !revealed">
          <button class="primary big" :disabled="paused" @click="revealed = true">{{ m.test.showAnswer }}</button>
        </template>
        <template v-else-if="!current.options && !decided">
          <button class="ok big" :disabled="paused" @click="judge('correct')">✓ {{ m.common.correct }}</button>
          <button class="bad big" :disabled="paused" @click="judge('wrong')">✗ {{ m.common.wrong }}</button>
        </template>
        <button v-if="decided" class="primary big" :disabled="paused" @click="next">{{ m.test.next }}</button>
      </div>
      <div class="controls secondary">
        <button v-if="!decided" :disabled="paused" @click="skip">{{ m.test.skip }}</button>
        <button @click="togglePause">{{ paused ? m.common.resume : m.common.pause }}</button>
        <button @click="finish('done')">{{ m.test.finish }}</button>
      </div>
      <p class="small muted center">{{ m.test.keys }}</p>
    </div>

    <template v-else-if="phase === 'over'">
      <div class="over" :class="{ timeup: endReason === 'time' }">
        <div class="over-title">{{ endReason === "time" ? m.test.timeUp : m.test.allDone }}</div>
        <div v-if="endReason === 'done' && timer.remaining.value > 0" class="muted">
          {{ m.test.timeLeft(formatClock(timer.remaining.value)) }}
        </div>
      </div>
      <div class="tiles">
        <div class="tile ok"><div class="n">{{ counts.correct }}</div>{{ m.common.correct }}</div>
        <div class="tile bad"><div class="n">{{ counts.wrong }}</div>{{ m.common.wrong }}</div>
        <div class="tile"><div class="n">{{ counts.unanswered }}</div>{{ m.test.unanswered }}</div>
      </div>
      <details class="panel">
        <summary>{{ m.test.review }}</summary>
        <table>
          <tbody>
            <tr v-for="(q, i) in questions" :key="i">
              <td class="muted">{{ i + 1 }}</td>
              <td class="small muted">{{ questionText(q) }}</td>
              <td :class="arClass(q.shown)" class="cell-big">{{ q.shown }}</td>
              <td :class="arClass(q.answer)" class="cell-big">{{ q.answer }}</td>
              <td>
                <span v-if="outcomes[i] === 'correct'" class="badge ok">{{ m.common.correct }}</span>
                <span v-else-if="outcomes[i] === 'wrong'" class="badge err">{{ m.common.wrong }}</span>
                <span v-else-if="outcomes[i] === 'skipped'" class="badge warn">{{ m.common.skipped }}</span>
                <span v-else class="badge">{{ m.test.unanswered }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </details>
      <p v-if="saved" class="small muted center">{{ m.results.saved }} <RouterLink to="/results">{{ m.nav.results }}</RouterLink></p>
      <div class="actions">
        <button class="primary" @click="begin">{{ m.common.restart }}</button>
        <button @click="phase = 'setup'">{{ m.common.settings }}</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.intro { max-width: 760px; }
.setup { display: flex; flex-direction: column; gap: 14px; margin-top: 16px; max-width: 560px; }
.hint { margin-top: -8px; }

.stage { display: flex; flex-direction: column; gap: 14px; max-width: 980px; margin: 0 auto; }
.stage-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 18px; }
.score { display: flex; gap: 6px; }
.clock { font-size: 44px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--accent); }
.clock.low { color: var(--err); }

.card {
  position: relative; min-block-size: 34vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 16px; padding: 28px; text-align: center;
  background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
}
.prompt { font-size: clamp(44px, 8vw, 104px); line-height: 1.3; word-break: break-word; }
.prompt:not(.ar) { font-size: clamp(26px, 4vw, 48px); }
.question { font-size: clamp(20px, 2.6vw, 30px); font-weight: 600; }
.note { font-size: 20px; color: var(--muted); }
.answer { font-size: clamp(34px, 6vw, 76px); color: var(--ok); }
.answer:not(.ar) { font-size: clamp(22px, 3.6vw, 40px); }
.paused-badge {
  position: absolute; inset-block-start: 14px; inset-inline-end: 14px;
  background: var(--warn-soft); color: var(--warn); padding: 4px 12px; border-radius: 12px; font-weight: 600;
}

.options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.option {
  display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-radius: 10px;
  font-size: 22px; text-align: start; border-width: 2px;
}
.option .ar { font-size: 36px; line-height: 1.4; }
.letter {
  flex: none; inline-size: 34px; block-size: 34px; border-radius: 50%; display: grid; place-items: center;
  background: var(--surface-2); font-size: 16px; font-weight: 700;
}
.option.is-right { border-color: var(--ok); background: var(--ok-soft); }
.option.is-wrong { border-color: var(--err); background: var(--err-soft); }
.option.dim { opacity: .55; }
.controls { display: flex; justify-content: center; gap: 14px; flex-wrap: wrap; }
.center { text-align: center; }

.over { text-align: center; padding: 28px 16px 8px; }
.over-title { font-size: clamp(40px, 7vw, 84px); font-weight: 800; color: var(--accent); }
.over.timeup .over-title { color: var(--err); }
.tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 16px auto; max-width: 640px; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px; text-align: center; }
.tile .n { font-size: 36px; font-weight: 700; }
.tile.ok .n { color: var(--ok); }
.tile.bad .n { color: var(--err); }
details summary { cursor: pointer; font-weight: 600; }
details table { margin-top: 10px; }
.cell-big.ar { font-size: 24px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; justify-content: center; }
</style>
