import { defineConfig } from "vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(root, "..");

export default defineConfig({
  root,
  publicDir: "public",
  server: {
    port: 5173,
    open: false,
    fs: {
      allow: [repoRoot],
    },
  },
  resolve: {
    alias: {
      "@fixtures": path.resolve(repoRoot, "tests/fixtures"),
    },
  },
});
