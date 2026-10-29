<script setup lang="ts">
import { computed, onMounted } from "vue";
import { locale, locales, messages, useI18n } from "./i18n";
import { useEngineStore } from "./stores/engine";
import { theme, themes } from "./theme";

const store = useEngineStore();
const m = useI18n();
onMounted(() => store.connect());

const nav = computed(() => [
  { to: "/", label: m.value.nav.activity },
  { to: "/test", label: m.value.nav.test },
  { to: "/sets", label: m.value.nav.sets },
  { to: "/analysis", label: m.value.nav.analysis },
  { to: "/results", label: m.value.nav.results },
  { to: "/lexicon", label: m.value.nav.lexicon, secondary: true },
  { to: "/rules", label: m.value.nav.rules, secondary: true },
  { to: "/about", label: m.value.nav.about, secondary: true },
]);

const appVersion = __APP_VERSION__;

const engineError = computed(() =>
  store.errorCode === "desktop_only" ? m.value.engine.desktopOnly : store.error,
);
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="brand" :title="m.app.tagline">
        <span class="mark ar" aria-hidden="true">ص</span>
        <span class="name">ArabMorph AI</span>
      </div>
      <nav>
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-link" :class="{ secondary: item.secondary }">
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="tools">
        <div class="seg small" role="group" :aria-label="m.theme.label">
          <button v-for="t in themes" :key="t" type="button" :class="{ on: theme === t }" :aria-pressed="theme === t"
                  :title="`${m.theme.label}: ${m.theme.names[t]}`" @click="theme = t">
            <span class="ico" aria-hidden="true">{{ { light: "☀", dark: "☾", system: "◐" }[t] }}</span>{{ m.theme.names[t] }}
          </button>
        </div>
        <select v-model="locale" class="small" :aria-label="m.nav.language" :title="m.nav.language">
          <option v-for="l in locales" :key="l" :value="l">{{ messages[l].langName }}</option>
        </select>
      </div>
    </header>
    <main class="content">
      <RouterView />
    </main>
    <footer class="footer small muted">
      <span>ArabMorph AI · {{ m.app.version(appVersion) }}</span>
      <span class="engine-status">
        <template v-if="store.version">
          <span class="dot ok" />{{ m.engine.ok }} · {{ m.engine.stats(store.version.engine, store.version.rules, store.version.lexicon_entries) }}
        </template>
        <template v-else-if="store.error !== null">
          <span class="dot err" />{{ m.engine.down }}<span v-if="engineError"> — {{ engineError }}</span>
          <button class="retry" @click="store.connect()">{{ m.engine.retry }}</button>
        </template>
        <template v-else><span class="dot" />{{ m.engine.starting }}</template>
      </span>
    </footer>
  </div>
</template>

<style scoped>
.shell { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; height: 100%; }
.topbar {
  display: flex; align-items: center; gap: 20px;
  padding: 8px 20px; border-bottom: 1px solid var(--border); background: var(--surface);
}
.brand { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.mark {
  width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center;
  background: var(--accent); color: var(--on-accent); font-size: 22px; line-height: 1;
}
.name { font-weight: 600; font-size: 15px; white-space: nowrap; }
nav { display: flex; align-items: center; gap: 2px; flex: 1; min-inline-size: 0; flex-wrap: wrap; }
.nav-link { padding: 6px 12px; border-radius: 6px; color: var(--text); text-decoration: none; white-space: nowrap; }
.nav-link.secondary { color: var(--muted); }
.nav-link:not(.secondary) + .nav-link.secondary {
  margin-inline-start: 9px; position: relative;
}
.nav-link:not(.secondary) + .nav-link.secondary::before {
  content: ""; position: absolute; inset-inline-start: -6px; top: 20%; bottom: 20%;
  border-inline-start: 1px solid var(--border);
}
.nav-link:hover { background: var(--surface-2); }
.nav-link.router-link-exact-active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.tools { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.seg { display: flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.seg button {
  display: flex; align-items: center; gap: 4px;
  border: 0; border-radius: 0; padding: 4px 9px; font-size: 12px; background: var(--surface); white-space: nowrap;
}
.seg .ico { font-size: 14px; }
.seg button + button { border-inline-start: 1px solid var(--border); }
.seg button.on { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.tools select { padding: 4px 8px; }
.content { overflow: auto; padding: 24px 28px; }
.footer {
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  padding: 6px 20px; border-top: 1px solid var(--border); background: var(--surface);
}
.engine-status { display: inline-flex; align-items: center; gap: 2px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--muted); margin-inline-end: 6px; }
.dot.ok { background: var(--ok); }
.dot.err { background: var(--err); }
.retry { margin-inline-start: 8px; font-size: 12px; padding: 1px 8px; }
</style>
