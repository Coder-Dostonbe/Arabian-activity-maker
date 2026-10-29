<script setup lang="ts">
import { ref } from "vue";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";

const store = useEngineStore();
const m = useI18n();
const logError = ref<string | null>(null);

async function openLogs() {
  logError.value = null;
  try {
    await invoke("open_log_folder");
  } catch (e) {
    logError.value = String(e);
  }
}
</script>

<template>
  <section class="about">
    <h1>{{ m.about.title }}</h1>
    <div class="panel">
      <h2>{{ m.about.heading }}</h2>
      <p v-if="store.version">
        {{ m.about.engine(store.version.engine, store.version.rules, store.version.lexicon_entries, store.version.lexicon_sources.join(", ")) }}
      </p>
      <p>{{ m.about.privacy }}</p>
      <p class="small muted">{{ m.about.logsHint }}</p>
      <div><button :disabled="!isTauri()" @click="openLogs">{{ m.about.openLogs }}</button></div>
      <div v-if="logError" class="notice err">{{ logError }}</div>
    </div>
    <div class="panel">
      <h2>{{ m.about.whatTitle }}</h2>
      <ul>
        <li v-for="line in m.about.what" :key="line">{{ line }}</li>
      </ul>
    </div>
    <div class="panel">
      <h2>{{ m.about.limitsTitle }}</h2>
      <ul>
        <li v-for="line in m.about.limits" :key="line">{{ line }}</li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.about { display: flex; flex-direction: column; gap: 12px; max-width: 760px; }
.about h1 { margin-bottom: 4px; }
ul { margin: 0; padding-inline-start: 20px; }
</style>
