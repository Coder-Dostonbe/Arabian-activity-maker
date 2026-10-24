<script setup lang="ts">
import { watchEffect } from "vue";
import { useI18n } from "../i18n";
import { useSetsStore } from "../stores/sets";

// Choose one of the sets that has approved rows; keeps the choice valid when sets change.
const model = defineModel<string | null>({ required: true });
const sets = useSetsStore();
const m = useI18n();

watchEffect(() => {
  if (!sets.usable.some((s) => s.id === model.value)) model.value = sets.usable[0]?.id ?? null;
});
</script>

<template>
  <div v-if="!sets.usable.length" class="notice warn">
    {{ m.common.noSets }}
    <RouterLink to="/sets">{{ m.common.goToSets }}</RouterLink>
  </div>
  <label v-else class="field">
    <span class="small muted">{{ m.common.set }}</span>
    <select v-model="model">
      <option v-for="s in sets.usable" :key="s.id" :value="s.id">
        {{ s.name }} — {{ m.common.approvedOf(s.items.filter((i) => i.approved).length, s.items.length) }}
      </option>
    </select>
  </label>
</template>
