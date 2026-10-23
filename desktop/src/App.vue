<script setup lang="ts">
import { onMounted } from "vue";
import { useEngineStore } from "./stores/engine";

const store = useEngineStore();
onMounted(() => store.connect());

const nav = [
  { to: "/", label: "Shakl yasash" },
  { to: "/lexicon", label: "Lug'at" },
  { to: "/rules", label: "Qoidalar" },
  { to: "/about", label: "Dastur haqida" },
];
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="mark ar" aria-hidden="true">ص</span>
        <div>
          <div class="name">ArabMorph AI</div>
          <div class="small muted">Arab morfologiyasi</div>
        </div>
      </div>
      <nav>
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-link">{{ item.label }}</RouterLink>
      </nav>
      <div class="engine-status small">
        <template v-if="store.version">
          <span class="dot ok" /> Oflayn dvigatel ishlayapti
          <div class="muted">v{{ store.version.engine }} · {{ store.version.rules }} qoida · {{ store.version.lexicon_entries }} so'z</div>
        </template>
        <template v-else-if="store.error">
          <span class="dot err" /> Dvigatel bilan aloqa yo'q
          <div class="muted">{{ store.error }}</div>
          <button class="retry" @click="store.connect()">Qayta urinish</button>
        </template>
        <template v-else><span class="dot" /> Dvigatel ishga tushmoqda…</template>
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
.nav-link:hover { background: var(--surface-2); }
.nav-link.router-link-exact-active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.engine-status { margin-top: auto; padding: 0 6px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--muted); margin-inline-end: 4px; }
.dot.ok { background: var(--ok); }
.dot.err { background: var(--err); }
.retry { margin-top: 6px; font-size: 12px; padding: 3px 8px; }
.content { overflow: auto; padding: 24px 28px; }
</style>
