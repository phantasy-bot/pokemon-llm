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
  // Use default publicDir ("public") for static assets like badges and sponsors
  // Access project root files via relative paths from fs.allow
});
