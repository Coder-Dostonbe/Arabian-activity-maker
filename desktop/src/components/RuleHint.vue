<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { Rule } from "../engine";
import { locale, useI18n } from "../i18n";
import { useEngineStore } from "../stores/engine";

// The rule(s) behind a correct form, for rows the engine built: name, explanation and example.
const props = withDefaults(defineProps<{ ids: string[]; limit?: number }>(), { limit: 2 });
const m = useI18n();
const store = useEngineStore();
const all = ref<Rule[]>([]);

onMounted(async () => {
  try {
    all.value = await store.loadRules();
  } catch {
    /* no engine: nothing to explain */
  }
});

const shown = computed(() =>
  props.ids.map((id) => all.value.find((r) => r.id === id)).filter((r): r is Rule => !!r).slice(0, props.limit),
);
// Rule texts exist in Arabic and English; Arabic for the Arabic interface, English otherwise.
const arabic = computed(() => locale.value === "ar");
</script>

<template>
  <div v-if="shown.length" class="rule-hint">
    <div class="label small">{{ m.tutor.label }}</div>
    <div v-for="r in shown" :key="r.id" class="rule">
      <div class="name ar" lang="ar" dir="rtl">{{ r.name_ar }}</div>
      <p :lang="arabic ? 'ar' : 'en'" :dir="arabic ? 'rtl' : 'ltr'" :class="{ ar: arabic }">
        {{ arabic ? r.explanation_ar : r.explanation_en }}
      </p>
      <div class="example ar" lang="ar" dir="rtl">{{ r.example }}</div>
    </div>
  </div>
</template>

<style scoped>
.rule-hint {
  border: 1px solid var(--border); border-inline-start: 4px solid var(--accent);
  border-radius: 8px; padding: 10px 14px; background: var(--surface); text-align: start;
  display: flex; flex-direction: column; gap: 8px;
}
.label { color: var(--accent); font-weight: 600; }
.name { font-size: 22px; font-weight: 600; }
.rule p { margin: 2px 0; }
.rule p.ar { font-size: 18px; }
.example { font-size: 22px; color: var(--muted); }
</style>
