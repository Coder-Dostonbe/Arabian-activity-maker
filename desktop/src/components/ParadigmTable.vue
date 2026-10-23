<script setup lang="ts">
import type { CaseName, GenerationResult, Paradigm, StateName } from "../engine";
import { caseLabel, stateLabel } from "../labels";

defineProps<{ paradigm: Paradigm; selected: string | null }>();
const emit = defineEmits<{ select: [key: string, result: GenerationResult] }>();

const states: StateName[] = ["indefinite", "definite", "construct"];
const cases: CaseName[] = ["nominative", "accusative", "genitive"];
</script>

<template>
  <table class="paradigm panel">
    <thead>
      <tr>
        <th></th>
        <th v-for="c in cases" :key="c">{{ caseLabel[c] }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="s in states" :key="s">
        <th scope="row">{{ stateLabel[s] }}</th>
        <td v-for="c in cases" :key="c">
          <button
            class="cell"
            :class="[paradigm[s][c].status, { active: selected === `${s}:${c}` }]"
            :aria-pressed="selected === `${s}:${c}`"
            @click="emit('select', `${s}:${c}`, paradigm[s][c])"
          >
            <template v-if="paradigm[s][c].forms.length">
              <span v-for="f in paradigm[s][c].forms" :key="f.vocalized + f.rules.join()" class="ar form" lang="ar">{{ f.vocalized }}</span>
            </template>
            <span v-else class="small muted">— yasab bo'lmadi</span>
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.paradigm { padding: 0; overflow: hidden; }
th[scope="row"] { white-space: nowrap; }
.cell {
  width: 100%; min-height: 56px; display: flex; flex-direction: column; align-items: flex-end;
  gap: 2px; background: none; border: 1px solid transparent; text-align: end;
}
.cell.active { border-color: var(--accent); background: var(--accent-soft); }
.cell.ambiguous { border-inline-start: 3px solid var(--warn); }
.cell.error { opacity: .7; }
.form { font-size: 26px; line-height: 1.4; }
</style>
