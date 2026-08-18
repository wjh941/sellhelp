import { build, preview } from 'vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import config from '../../vite.config.js'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
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
    port: 5187,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8005',
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
