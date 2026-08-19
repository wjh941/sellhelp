import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const startBackendScript = path.join(frontendRoot, 'tests', 'e2e', 'start-backend.cmd')

test('E2E backend helper accepts the caller-selected loopback port with an 8005 fallback', () => {
  const script = readFileSync(startBackendScript, 'utf8')

  assert.match(script, /if "%SELLHELP_E2E_BACKEND_PORT%"=="" set "SELLHELP_E2E_BACKEND_PORT=8005"/)
  assert.match(script, /--port %SELLHELP_E2E_BACKEND_PORT%/)
  assert.doesNotMatch(script, /--port 8005/)
})
