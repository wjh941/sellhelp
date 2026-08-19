import { build, preview } from 'vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import config from '../../vite.config.js'
import { readE2ePort, resolveE2eBackendUrl } from './runtime.mjs'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const frontendPort = readE2ePort(process.env.SELLHELP_E2E_FRONTEND_PORT, 5187, 'SELLHELP_E2E_FRONTEND_PORT')
const backendUrl = resolveE2eBackendUrl(process.env)
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
        target: backendUrl,
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
