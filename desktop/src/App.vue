<script setup lang="ts">
import { computed, onMounted } from "vue";
import { locale, locales, messages, useI18n } from "./i18n";
import { useEngineStore } from "./stores/engine";

const store = useEngineStore();
const m = useI18n();
onMounted(() => store.connect());

const nav = computed(() => [
  { to: "/", label: m.value.nav.activity },
  { to: "/test", label: m.value.nav.test },
  { to: "/sets", label: m.value.nav.sets },
  { to: "/lexicon", label: m.value.nav.lexicon, secondary: true },
  { to: "/rules", label: m.value.nav.rules, secondary: true },
  { to: "/about", label: m.value.nav.about, secondary: true },
]);

const engineError = computed(() =>
  store.errorCode === "desktop_only" ? m.value.engine.desktopOnly : store.error,
);
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="mark ar" aria-hidden="true">ص</span>
        <div>
          <div class="name">ArabMorph AI</div>
          <div class="small muted">{{ m.app.tagline }}</div>
        </div>
      </div>
      <nav>
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-link" :class="{ secondary: item.secondary }">
          {{ item.label }}
        </RouterLink>
      </nav>
      <label class="lang small">
        <span class="muted">{{ m.nav.language }}</span>
        <select v-model="locale" :aria-label="m.nav.language">
          <option v-for="l in locales" :key="l" :value="l">{{ messages[l].langName }}</option>
        </select>
      </label>
      <div class="engine-status small">
        <template v-if="store.version">
          <span class="dot ok" /> {{ m.engine.ok }}
          <div class="muted">{{ m.engine.stats(store.version.engine, store.version.rules, store.version.lexicon_entries) }}</div>
        </template>
        <template v-else-if="store.error !== null">
          <span class="dot err" /> {{ m.engine.down }}
          <div class="muted">{{ engineError }}</div>
          <button class="retry" @click="store.connect()">{{ m.engine.retry }}</button>
        </template>
        <template v-else><span class="dot" /> {{ m.engine.starting }}</template>
      </div>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell { display: grid; grid-template-columns: 220px 1fr; height: 100%; }
.sidebar {
  display: flex; flex-direction: column; gap: 16px;
  padding: 16px 12px; border-inline-end: 1px solid var(--border); background: var(--surface);
}
.brand { display: flex; align-items: center; gap: 10px; padding: 0 6px; }
.mark {
  width: 36px; height: 36px; border-radius: 8px; display: grid; place-items: center;
  background: var(--accent); color: #fff; font-size: 26px; line-height: 1;
}
.name { font-weight: 600; }
nav { display: flex; flex-direction: column; gap: 2px; }
.nav-link { padding: 7px 10px; border-radius: 6px; color: var(--text); text-decoration: none; }
.nav-link.secondary { color: var(--muted); }
.nav-link.secondary:first-of-type, .nav-link:not(.secondary) + .nav-link.secondary { margin-top: 10px; }
.nav-link:hover { background: var(--surface-2); }
.nav-link.router-link-exact-active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.lang { display: flex; flex-direction: column; gap: 4px; padding: 0 6px; margin-top: auto; }
.engine-status { padding: 0 6px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--muted); margin-inline-end: 4px; }
.dot.ok { background: var(--ok); }
.dot.err { background: var(--err); }
.retry { margin-top: 6px; font-size: 12px; padding: 3px 8px; }
.content { overflow: auto; padding: 24px 28px; }
</style>
