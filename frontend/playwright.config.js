import process from "node:process";
import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const directory = mkdtempSync(join(tmpdir(), "lendbot-browser-"));
const python = process.env.LENDBOT_PYTHON || "python";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 90000,
  use: { baseURL: "http://127.0.0.1:5181", channel: process.env.CHROME_CHANNEL || "chrome",
    viewport: {width: 1200, height: 900}, video: {mode: process.env.RECORD_DEMO ? "on" : "off", size: {width: 1200, height: 900}} },
  webServer: [
    { command: '"' + python + '" -m uvicorn app.main:app --host 127.0.0.1 --port 8019',
      cwd: "../backend", url: "http://127.0.0.1:8019/health", timeout: 90000,
      env: { DATABASE_URL: "sqlite:///" + join(directory, "applications.db").replaceAll("\\", "/"),
        LEGACY_REDIS_URL: "", GEMINI_API_KEY: "", ALLOWED_ORIGIN: "http://127.0.0.1:5181" } },
    { command: "npm run dev -- --host 127.0.0.1 --port 5181 --strictPort", url: "http://127.0.0.1:5181",
      env: { VITE_API_URL: "http://127.0.0.1:8019" } }
  ]
});
