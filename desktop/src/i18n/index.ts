// Interface language: switched entirely in the UI, remembered on this computer.
import { computed, ref, watchEffect } from "vue";
import { ar } from "./ar";
import { en } from "./en";
import { ru } from "./ru";
import { uz, type Messages } from "./uz";
import { readStorage, writeStorage } from "../util";

export type Locale = "uz" | "ar" | "ru" | "en";

export const messages: Record<Locale, Messages> = { uz, ar, ru, en };
export const locales = Object.keys(messages) as Locale[];

const KEY = "arabmorph.locale";
const saved = readStorage<string>(KEY, "uz");

export const locale = ref<Locale>(locales.includes(saved as Locale) ? (saved as Locale) : "uz");

watchEffect(() => {
  writeStorage(KEY, locale.value);
  document.documentElement.lang = locale.value;
  document.documentElement.dir = locale.value === "ar" ? "rtl" : "ltr";
});

const current = computed(() => messages[locale.value]);

/** The active messages; `const m = useI18n()` then `m.value.nav.test` in script, `m.nav.test` in templates. */
export function useI18n() {
  return current;
}
