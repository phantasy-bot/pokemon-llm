import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    fs: {
      allow: [".."], // Allow serving files from parent directory (project root)
    },
  },
  publicDir: "../", // Set public directory to project root for latest.png access
});
