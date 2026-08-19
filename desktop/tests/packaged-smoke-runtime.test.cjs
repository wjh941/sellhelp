const assert = require('node:assert/strict')
const test = require('node:test')

const {
  findPackagedWindowTarget,
  isReadyPackagedWindowState,
} = require('./packaged-smoke-runtime.cjs')

test('packaged smoke selects only a same-origin Electron page target', () => {
  const origin = 'http://127.0.0.1:18115'
  const target = findPackagedWindowTarget([
    { type: 'service_worker', url: `${origin}/worker.js`, webSocketDebuggerUrl: 'ws://ignored' },
    { type: 'page', url: 'https://example.test/', webSocketDebuggerUrl: 'ws://ignored' },
    { type: 'page', url: `${origin}/`, webSocketDebuggerUrl: 'ws://target' },
  ], origin)

  assert.deepEqual(target, { type: 'page', url: `${origin}/`, webSocketDebuggerUrl: 'ws://target' })
})

test('packaged smoke accepts a populated app root only at its backend origin', () => {
  const origin = 'http://127.0.0.1:18115'

  assert.equal(isReadyPackagedWindowState({ origin, appChildCount: 1 }, origin), true)
  assert.equal(isReadyPackagedWindowState({ origin, appChildCount: 0 }, origin), false)
  assert.equal(isReadyPackagedWindowState({ origin: 'http://127.0.0.1:18116', appChildCount: 1 }, origin), false)
})
