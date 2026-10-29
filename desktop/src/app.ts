import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import ActivityView from "./views/ActivityView.vue";
import TestView from "./views/TestView.vue";
import SetsView from "./views/SetsView.vue";
import LexiconView from "./views/LexiconView.vue";
import RulesView from "./views/RulesView.vue";
import AboutView from "./views/AboutView.vue";
import "./i18n";
import "./theme";
import "@fontsource-variable/noto-sans";
import "@fontsource-variable/noto-sans-arabic";
import "./style.css";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", component: ActivityView },
    { path: "/test", component: TestView },
    { path: "/sets", component: SetsView },
    { path: "/lexicon", component: LexiconView },
    { path: "/rules", component: RulesView },
    { path: "/about", component: AboutView },
  ],
});

export function start() {
  createApp(App).use(createPinia()).use(router).mount("#app");
}
