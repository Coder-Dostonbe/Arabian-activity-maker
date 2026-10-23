import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import GenerateView from "./views/GenerateView.vue";
import LexiconView from "./views/LexiconView.vue";
import RulesView from "./views/RulesView.vue";
import AboutView from "./views/AboutView.vue";
import "./style.css";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", component: GenerateView },
    { path: "/lexicon", component: LexiconView },
    { path: "/rules", component: RulesView },
    { path: "/about", component: AboutView },
  ],
});

createApp(App).use(createPinia()).use(router).mount("#app");
