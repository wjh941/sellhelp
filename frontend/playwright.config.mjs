import { defineConfig } from '@playwright/test'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.dirname(fileURLToPath(import.meta.url))
const backendRoot = path.resolve(frontendRoot, '../backend')
const testDatabase = path.join(tmpdir(), `sellhelp-playwright-${Date.now()}-${process.pid}.db`).replaceAll('\\', '/')
const backendUrl = 'http://127.0.0.1:8005'
const systemEdge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const usesManagedServers = process.env.SELLHELP_E2E_MANAGED_SERVERS === '1'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5187',
    launchOptions: {
      executablePath: systemEdge,
    },
    trace: 'retain-on-failure',
  },
  ...(usesManagedServers ? {} : {
    webServer: [
      {
        command: 'cmd /d /s /c ..\\frontend\\tests\\e2e\\start-backend.cmd',
        cwd: backendRoot,
        env: {
          SELLHELP_DATABASE_URL: `sqlite:///${testDatabase}`,
          SELLHELP_DISABLE_MARKET_SYNC_SCHEDULER: '1',
          SELLHELP_JWT_SECRET: 'sellhelp-playwright-secret-key-000000',
        },
        url: `${backendUrl}/api/health`,
        reuseExistingServer: false,
      },
      {
        command: 'node tests/e2e/start-frontend.mjs',
        cwd: frontendRoot,
        url: 'http://127.0.0.1:5187',
        reuseExistingServer: false,
      },
    ],
  }),
})
