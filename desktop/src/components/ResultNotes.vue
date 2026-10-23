<script setup lang="ts">
import type { GenerationResult } from "../engine";
import { statusLabel } from "../labels";

defineProps<{ result: GenerationResult }>();
</script>

<template>
  <div class="notes">
    <div class="notice" :class="{ ok: result.status === 'ok', warn: result.status === 'ambiguous', err: result.status === 'error' }">
      <strong>{{ statusLabel[result.status] }}</strong>
      <span v-if="result.status === 'ambiguous'"> — dalillar bitta javobni tanlashga yetmaydi; har bir shaklning sharti ko'rsatilgan.</span>
    </div>
    <div v-for="e in result.errors" :key="e" class="notice err">{{ e }}</div>
    <div v-for="w in result.warnings" :key="w" class="notice warn small">{{ w }}</div>
    <details class="small muted">
      <summary>Farazlar</summary>
      <ul>
        <li v-for="a in result.assumptions" :key="a">{{ a }}</li>
      </ul>
    </details>
  </div>
</template>

<style scoped>
.notes { margin-bottom: 12px; }
details { margin-top: 4px; }
</style>
