import { build, preview } from 'vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import config from '../../vite.config.js'
import { readE2ePort } from './runtime.mjs'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const backendPort = readE2ePort(process.env.SELLHELP_E2E_BACKEND_PORT, 8005, 'SELLHELP_E2E_BACKEND_PORT')
const frontendPort = readE2ePort(process.env.SELLHELP_E2E_FRONTEND_PORT, 5187, 'SELLHELP_E2E_FRONTEND_PORT')
await build({
  ...config,
  configFile: false,
  root: frontendRoot,
  build: {
    ...config.build,
    outDir: path.join(frontendRoot, 'dist-e2e'),
    emptyOutDir: true,
  },
})

const server = await preview({
  ...config,
  configFile: false,
  root: frontendRoot,
  build: {
    ...config.build,
    outDir: path.join(frontendRoot, 'dist-e2e'),
  },
  preview: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
})

server.printUrls()

const shutdown = async () => {
  await server.close()
  process.exit(0)
}

process.once('SIGINT', shutdown)
process.once('SIGTERM', shutdown)
