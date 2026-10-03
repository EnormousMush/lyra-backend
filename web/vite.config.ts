import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The API port comes from dev.sh (LYRA_API_PORT, default 8765). Proxying /api keeps the
// session cookie same-origin, so the web port does not matter.
const apiPort = process.env.LYRA_API_PORT || "8765";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { "/api": { target: `http://127.0.0.1:${apiPort}`, changeOrigin: false } },
  },
});
