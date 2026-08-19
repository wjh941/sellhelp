import assert from 'node:assert/strict'
import test from 'node:test'

import {
  createManagedE2eRuntime,
  findLoopbackPort,
  resolveE2eBackendUrl,
} from './e2e/runtime.mjs'

test('managed E2E runtime passes distinct dynamic loopback ports to every child', () => {
  const runtime = createManagedE2eRuntime({ backendPort: 18115, frontendPort: 18116 })

  assert.equal(runtime.backendUrl, 'http://127.0.0.1:18115')
  assert.equal(runtime.frontendUrl, 'http://127.0.0.1:18116')
  assert.deepEqual(runtime.childEnvironment, {
    SELLHELP_E2E_BACKEND_PORT: '18115',
    SELLHELP_E2E_BACKEND_URL: 'http://127.0.0.1:18115',
    SELLHELP_E2E_FRONTEND_PORT: '18116',
    SELLHELP_E2E_FRONTEND_URL: 'http://127.0.0.1:18116',
  })
})

test('loopback port allocator returns a usable TCP port number', async () => {
  const port = await findLoopbackPort()

  assert.equal(Number.isInteger(port), true)
  assert.ok(port > 0 && port < 65536)
})

test('custom E2E backend port also determines the API origin without a separate URL variable', () => {
  assert.equal(resolveE2eBackendUrl({ SELLHELP_E2E_BACKEND_PORT: '18115' }), 'http://127.0.0.1:18115')
  assert.equal(
    resolveE2eBackendUrl({
      SELLHELP_E2E_BACKEND_PORT: '18115',
      SELLHELP_E2E_BACKEND_URL: 'http://127.0.0.1:19115',
    }),
    'http://127.0.0.1:19115',
  )
})
