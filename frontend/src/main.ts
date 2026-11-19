import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/styles/shared.css";

const app = createApp(App);

// Pinia must be registered before the router because the navigation guard
// in router/index.ts calls useAuthStore() at runtime.
app.use(createPinia());
app.use(router);

app.mount("#app");
