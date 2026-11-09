import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The build goes straight into the Flask package, which serves it (same origin, no CORS).
// In development, Vite proxies the API to Flask on :5000 so cookies still work.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../nexus/static/app",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5000",
      "/healthz": "http://127.0.0.1:5000",
    },
  },
});
