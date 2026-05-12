import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: [".monkeycode-ai.online"],
    proxy: {
      "/api": {
        target: "http://backend-api:8000",
        changeOrigin: true,
      },
    },
  },
});
