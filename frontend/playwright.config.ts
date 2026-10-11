import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
const chromiumPath =
  process.env.CHROMIUM_PATH || (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
export default defineConfig({
  testDir: './e2e',
  timeout: 120000,
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
    launchOptions: {
      executablePath: chromiumPath,
      args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    },
  },
  reporter: [['list'], ['json', { outputFile: 'test-results/results.json' }]],
});
