<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { Rule } from "../engine";
import { locale, useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";

const store = useEngineStore();
const m = useI18n();
const rules = ref<Rule[]>([]);
const failure = ref<string | null>(null);

const groups = computed(() => {
  const out: { key: string; title: string; rules: Rule[] }[] = [];
  for (const r of rules.value) {
    const key = r.id.split(".")[0];
    let g = out.find((x) => x.key === key);
    if (!g) out.push((g = { key, title: m.value.rules.groups[key] ?? key, rules: [] }));
    g.rules.push(r);
  }
  return out;
});

onMounted(async () => {
  try {
    rules.value = await store.loadRules();
  } catch (e) {
    failure.value = (e as Error).message;
  }
});
</script>

<template>
  <section>
    <h1>{{ m.rules.title }}</h1>
    <p class="muted">{{ m.rules.intro }}</p>
    <div v-if="failure" class="notice err">{{ failure }}</div>
    <div v-for="g in groups" :key="g.key" class="group">
      <h2>{{ g.title }} <span class="muted small">({{ g.rules.length }})</span></h2>
      <article v-for="r in g.rules" :key="r.id" class="panel rule">
        <div class="head">
          <div class="ar name" lang="ar">{{ r.name_ar }}</div>
          <code class="small muted">{{ r.id }}</code>
        </div>
        <p class="ar" lang="ar">{{ r.explanation_ar }}</p>
        <!-- The engine explains rules in Arabic and English only. -->
        <p v-if="locale !== 'ar'" class="muted" lang="en" dir="ltr">{{ r.explanation_en }}</p>
        <p class="ar example" lang="ar">{{ r.example }}</p>
        <p class="small muted">{{ m.rules.reference }}: {{ r.reference }}</p>
        <span class="badge warn">{{ m.rules.pending }}</span>
      </article>
    </div>
  </section>
</template>

<style scoped>
.group { margin-top: 20px; }
.rule { margin-bottom: 10px; }
.head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.name { font-size: 22px; font-weight: 600; }
.ar { font-size: 18px; }
.example { font-size: 22px; color: var(--accent); }
</style>
