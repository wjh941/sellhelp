import { defineConfig } from '@playwright/test'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { readE2ePort } from './tests/e2e/runtime.mjs'

const frontendRoot = path.dirname(fileURLToPath(import.meta.url))
const backendRoot = path.resolve(frontendRoot, '../backend')
const testDatabase = path.join(tmpdir(), `sellhelp-playwright-${Date.now()}-${process.pid}.db`).replaceAll('\\', '/')
const backendPort = readE2ePort(process.env.SELLHELP_E2E_BACKEND_PORT, 8005, 'SELLHELP_E2E_BACKEND_PORT')
const frontendPort = readE2ePort(process.env.SELLHELP_E2E_FRONTEND_PORT, 5187, 'SELLHELP_E2E_FRONTEND_PORT')
const backendUrl = `http://127.0.0.1:${backendPort}`
const frontendUrl = `http://127.0.0.1:${frontendPort}`
const systemEdge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const usesManagedServers = process.env.SELLHELP_E2E_MANAGED_SERVERS === '1'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: frontendUrl,
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
        url: frontendUrl,
        reuseExistingServer: false,
      },
    ],
  }),
})
