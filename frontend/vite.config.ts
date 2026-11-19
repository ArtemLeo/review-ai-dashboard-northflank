import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ mode }) => {
  // Load the VITE_* variables from the .env files of the current mode.
  const env = loadEnv(mode, fileURLToPath(new URL(".", import.meta.url)), "VITE_");

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      port: 4200,
      proxy: {
        "/api": {
          target: env.VITE_API_URL ?? "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    build: {
      // Split the vendor bundle so that framework code stays cached
      // independently from the application code.
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ["vue", "vue-router", "pinia", "axios"],
          },
        },
      },
    },
  };
});
