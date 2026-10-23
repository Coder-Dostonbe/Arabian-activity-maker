<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { Rule } from "../engine";
import { useEngineStore } from "../stores/engine";

const store = useEngineStore();
const rules = ref<Rule[]>([]);
const failure = ref<string | null>(null);

const groups = computed(() => {
  const names: Record<string, string> = { dual: "Ikkilik", decl: "I'rob (kelishik qo'shimchalari)", plural: "Ko'plik", context: "Kontekst" };
  const out: { key: string; title: string; rules: Rule[] }[] = [];
  for (const r of rules.value) {
    const key = r.id.split(".")[0];
    let g = out.find((x) => x.key === key);
    if (!g) out.push((g = { key, title: names[key] ?? key, rules: [] }));
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
    <h1>Qoidalar</h1>
    <p class="muted">Dvigatelda amalga oshirilgan va testlar bilan qamralgan qoidalar. Hammasi mutaxassis ko'rigini kutmoqda.</p>
    <div v-if="failure" class="notice err">{{ failure }}</div>
    <div v-for="g in groups" :key="g.key" class="group">
      <h2>{{ g.title }} <span class="muted small">({{ g.rules.length }})</span></h2>
      <article v-for="r in g.rules" :key="r.id" class="panel rule">
        <div class="head">
          <div class="ar name" lang="ar">{{ r.name_ar }}</div>
          <code class="small muted">{{ r.id }}</code>
        </div>
        <p class="ar" lang="ar">{{ r.explanation_ar }}</p>
        <p class="muted">{{ r.explanation_en }}</p>
        <p class="ar example" lang="ar">{{ r.example }}</p>
        <p class="small muted">Manba: {{ r.reference }}</p>
        <span class="badge warn">Ko'rik kutilmoqda</span>
      </article>
    </div>
  </section>
</template>

<style scoped>
.group { margin-top: 20px; }
.rule { margin-bottom: 10px; }
.head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-direction: row-reverse; }
.name { font-size: 22px; font-weight: 600; }
.ar { font-size: 18px; }
.example { font-size: 22px; color: var(--accent); }
</style>
