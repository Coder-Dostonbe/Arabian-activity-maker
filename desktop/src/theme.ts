// Day / night mode: "system" follows Windows, the other two override it. Remembered on this computer.
import { watchEffect } from "vue";
import { persisted } from "./util";

export type Theme = "system" | "light" | "dark";
export const themes: Theme[] = ["light", "dark", "system"];

export const theme = persisted<Theme>("arabmorph.theme", "system");
if (!themes.includes(theme.value)) theme.value = "system";

watchEffect(() => {
  const root = document.documentElement;
  if (theme.value === "system") delete root.dataset.theme;
  else root.dataset.theme = theme.value;
});
